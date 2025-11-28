import io
import pandas as pd
from backend.service.auth import get_password_hash
import numpy as np
from typing import Dict, Any, List
from fastapi import UploadFile, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

# Ensure this import points to your actual models file location
from backend.models import User, UserProfile 

class ImportService:
    """
    Handles bulk import of Users and their Profiles.
    """

    # Maps CSV headers to DB columns
    # Keys = Normalized CSV Headers (lowercase, spaces replaced by underscores)
    # Values = Exact Database Column Names
    
    USER_MAPPING = {
        "email": "email",
        "login": "email",
        "username": "email",
        "password": "password",
        "pass": "password"
    }

    PROFILE_MAPPING = {
        # --- Basic Info ---
        "first_name": "first_name",
        "firstname": "first_name",
        "last_name": "last_name",
        "lastname": "last_name",
        "bio": "bio",
        "major": "major",
        "department": "major",
        "university": "university",
        "affiliation": "university",

        # --- Scientific IDs ---
        "google_scholar_id": "google_scholar_id",
        "google_scholar": "google_scholar_id",
        "gs_id": "google_scholar_id",
        
        "scopus_id": "scopus_id",
        "scopus": "scopus_id",
        
        "orcid": "orcid",
        "orcid_id": "orcid",
        
        "arxiv_name": "arxiv_name",
        "arxiv": "arxiv_name",
        
        "semantic_scholar_id": "semantic_scholar_id",
        "semantic_scholar": "semantic_scholar_id",

        # --- Metrics ---
        # Note: Ensure CSV contains clean numbers for these.
        "citations_total": "citations_total",
        "citations": "citations_total",
        "total_citations": "citations_total",
        
        "citations_recent": "citations_recent",
        "recent_citations": "citations_recent",
        
        "h_index": "h_index",
        "hindex": "h_index",
        "h-index": "h_index", # Normalized CSV might still have hyphens
        
        "i10_index": "i10_index",
        "i10": "i10_index",
        "i10-index": "i10_index",
        
        "publication_count": "publication_count",
        "publications": "publication_count",
        "paper_count": "publication_count"
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_import_file(self, file: UploadFile) -> Dict[str, Any]:
        # 1. Read and Clean Data
        df = await self._read_file_to_df(file)
        df = self._clean_dataframe(df)

        # 2. Process Users (Create new accounts if needed, get IDs)
        email_to_id_map = await self._process_users(df)

        # 3. Process Profiles (Link to user_ids and Upsert)
        result = await self._upsert_profiles(df, email_to_id_map)

        return result

    async def _read_file_to_df(self, file: UploadFile) -> pd.DataFrame:
        contents = await file.read()
        buffer = io.BytesIO(contents)
        try:
            if file.filename.endswith('.csv'):
                return pd.read_csv(buffer)
            elif file.filename.endswith(('.xls', '.xlsx')):
                return pd.read_excel(buffer)
            else:
                raise HTTPException(status_code=400, detail="Invalid format.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Parse error: {e}")

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise HTTPException(status_code=400, detail="File is empty.")

        # Normalize Headers: lowercase, strip spaces, replace space with underscore
        # Note: This does NOT replace hyphens, so 'h-index' stays 'h-index'
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # Check required columns for User creation
        has_email = any(col in df.columns for col in ["email", "login", "username"])
        if not has_email:
            raise HTTPException(status_code=400, detail="File must contain 'email' or 'login' column.")

        return df

    async def _process_users(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Ensures all users in DF exist in DB. Returns a dict {email: user_id}.
        """
        # Identify email/password columns based on mapping
        email_col = next((c for c in df.columns if c in self.USER_MAPPING and self.USER_MAPPING[c] == 'email'), None)
        password_col = next((c for c in df.columns if c in self.USER_MAPPING and self.USER_MAPPING[c] == 'password'), None)

        if not email_col:
            raise HTTPException(status_code=400, detail="Could not identify email column.")
        
        # Extract unique emails
        input_emails = df[email_col].dropna().unique().tolist()

        # Find existing users
        result = await self.db.execute(select(User.email, User.id).where(User.email.in_(input_emails)))
        existing_users = result.all()
        email_to_id = {u.email: u.id for u in existing_users}

        # Filter for NEW users
        new_users_df = df[~df[email_col].isin(email_to_id.keys())].copy()
        new_users_df = new_users_df.drop_duplicates(subset=[email_col])

        if not new_users_df.empty:
            if not password_col:
                 raise HTTPException(status_code=400, detail="New users found, but no 'password' column provided.")

            new_user_records = []
            for _, row in new_users_df.iterrows():
                raw_pwd = str(row[password_col]) if pd.notna(row[password_col]) else "default123"
                
                new_user_records.append({
                    "email": row[email_col],
                    "hashed_password": get_password_hash(raw_pwd),
                    "role": "observer",
                    "is_active": True
                })

            # Bulk Insert
            stmt = insert(User).values(new_user_records).returning(User.id, User.email)
            result = await self.db.execute(stmt)
            newly_created = result.all()

            for row in newly_created:
                email_to_id[row.email] = row.id

        return email_to_id

    async def _upsert_profiles(self, df: pd.DataFrame, email_to_id: Dict[str, int]) -> Dict[str, Any]:
        """
        Upserts UserProfile records using the user_ids mapped from emails.
        """
        email_col = next((c for c in df.columns if c in self.USER_MAPPING and self.USER_MAPPING[c] == 'email'), None)
        
        profile_records = []

        for _, row in df.iterrows():
            email = row[email_col]
            user_id = email_to_id.get(email)
            
            if not user_id:
                continue

            record = {"user_id": user_id}
            
            # Map CSV columns to Profile Model columns
            for csv_col, db_col in self.PROFILE_MAPPING.items():
                if csv_col in df.columns:
                    val = row[csv_col]
                    # Handle Pandas NaN -> None
                    # For Integer fields (h_index, citations), ensure clean input in CSV
                    record[db_col] = val if pd.notna(val) else None

            profile_records.append(record)

        if not profile_records:
            return {"status": "skipped", "message": "No profile data found."}

        try:
            stmt = insert(UserProfile).values(profile_records)

            # Update all columns except primary keys on conflict
            update_dict = {
                col.name: stmt.excluded[col.name]
                for col in UserProfile.__table__.columns
                if col.name not in ['id', 'user_id']
            }

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=['user_id'],
                set_=update_dict
            )

            await self.db.execute(upsert_stmt)
            await self.db.commit()

            return {
                "status": "success",
                "users_processed": len(email_to_id),
                "profiles_upserted": len(profile_records)
            }

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error during profile import: {str(e)}")
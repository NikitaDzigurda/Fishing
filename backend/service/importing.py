import io
import pandas as pd
from backend.service.auth import get_password_hash
import numpy as np
from typing import Dict, Any, List
from fastapi import UploadFile, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from backend.models import User, UserProfile

class ImportService:
    """
    Handles bulk import of Users and their Profiles.
    """

    # Maps CSV headers to DB columns
    # Split into two sets: User fields and Profile fields
    USER_MAPPING = {
        "email": "email",
        "login": "email",  # mapping 'login' to 'email' field
        "username": "email",
        "password": "password",
        "pass": "password"
    }

    PROFILE_MAPPING = {
        "first_name": "first_name",
        "firstname": "first_name",
        "last_name": "last_name",
        "lastname": "last_name",
        "bio": "bio",
        "major": "major",
        "department": "major",
        "university": "university",
        "affiliation": "university"
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

        # Normalize Headers
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # Check required columns for User creation
        # We need at least an email/login column
        has_email = any(col in df.columns for col in ["email", "login", "username"])
        if not has_email:
            raise HTTPException(status_code=400, detail="File must contain 'email' or 'login' column.")

        return df

    async def _process_users(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Ensures all users in DF exist in DB. Returns a dict {email: user_id}.
        """
        # 1. Standardize the 'email' column in the DataFrame
        # Find which column corresponds to email based on mapping
        email_col = next((c for c in df.columns if c in self.USER_MAPPING and self.USER_MAPPING[c] == 'email'), None)
        password_col = next((c for c in df.columns if c in self.USER_MAPPING and self.USER_MAPPING[c] == 'password'), None)

        if not email_col:
            raise HTTPException(status_code=400, detail="Could not identify email column.")
        
        # Extract unique emails from file
        input_emails = df[email_col].dropna().unique().tolist()

        # 2. Find existing users in DB
        result = await self.db.execute(select(User.email, User.id).where(User.email.in_(input_emails)))
        existing_users = result.all() # list of (email, id) tuples
        email_to_id = {u.email: u.id for u in existing_users}

        # 3. Filter for NEW users
        new_users_df = df[~df[email_col].isin(email_to_id.keys())].copy()
        
        # Deduplicate by email (in case CSV has duplicates)
        new_users_df = new_users_df.drop_duplicates(subset=[email_col])

        if not new_users_df.empty:
            if not password_col:
                 raise HTTPException(status_code=400, detail="New users found, but no 'password' column provided.")

            # Prepare records for insertion
            new_user_records = []
            for _, row in new_users_df.iterrows():
                raw_pwd = str(row[password_col]) if pd.notna(row[password_col]) else "default123" # Fallback or error
                
                new_user_records.append({
                    "email": row[email_col],
                    "hashed_password": get_password_hash(raw_pwd),
                    "role": "observer", # default
                    "is_active": True
                })

            # Bulk Insert and Return IDs
            # returning(User.id, User.email) allows us to get the generated IDs immediately
            stmt = insert(User).values(new_user_records).returning(User.id, User.email)
            result = await self.db.execute(stmt)
            newly_created = result.all()

            # Add new IDs to our map
            for row in newly_created:
                email_to_id[row.email] = row.id

        return email_to_id

    async def _upsert_profiles(self, df: pd.DataFrame, email_to_id: Dict[str, int]) -> Dict[str, Any]:
        """
        Upserts UserProfile records using the user_ids mapped from emails.
        """
        # Identify email column again
        email_col = next((c for c in df.columns if c in self.USER_MAPPING and self.USER_MAPPING[c] == 'email'), None)
        
        # Prepare Profile Records
        profile_records = []

        # Iterate through DF to build profile dicts
        for _, row in df.iterrows():
            email = row[email_col]
            user_id = email_to_id.get(email)
            
            if not user_id:
                continue # Should not happen given logic above

            # Map CSV columns to Profile Model columns
            record = {"user_id": user_id}
            
            for csv_col, db_col in self.PROFILE_MAPPING.items():
                if csv_col in df.columns:
                    val = row[csv_col]
                    # Handle Pandas NaN -> None
                    record[db_col] = val if pd.notna(val) else None

            profile_records.append(record)

        if not profile_records:
            return {"status": "skipped", "message": "No profile data found."}

        try:
            stmt = insert(UserProfile).values(profile_records)

            # Upsert Logic: Update profile fields if user_id exists
            update_dict = {
                col.name: stmt.excluded[col.name]
                for col in UserProfile.__table__.columns
                if col.name not in ['id', 'user_id']
            }

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=['user_id'], # Unique constraint on UserProfile
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
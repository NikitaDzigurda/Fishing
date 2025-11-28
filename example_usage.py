from vector_db import AuthorSearchEngine
from recsys import RecSys


# 1. Подготовка тестовых данных (Ваша структура)
import random

users_data = {
    101: {
        "combined": {
            "name": "Dr. Alice Smith",
            "interests": ["Machine Learning", "NLP", "Transformers"],
            "publications": [
                {"title": "Attention is all you need",
                 "abstract": "We propose a new simple network architecture based solely on attention mechanisms.",
                 "year": 2017,
                 "authors": [101, 103, 402, 881]},
                {"title": "BERT embeddings",
                 "abstract": "Deep bidirectional transformers for language understanding.",
                 "year": 2019,
                 "authors": [101, 550]}
            ]
        }
    },
    102: {
        "combined": {
            "name": "Prof. Bob Jones",
            "interests": ["Biology", "Genetics", "Cells"],
            "publications": [
                {"title": "CRISPR gene editing", "abstract": "A precise method for editing genomic DNA.",
                 "year": 2020,
                 "authors": [102, 113, 604]},
                {"title": "Cell division mechanics", "abstract": "Study of mitosis in eukaryotic cells.",
                 "year": 2016,
                 "authors": [102, 701, 702]}
            ]
        }
    },
    103: {
        "combined": {
            "name": "Charlie Brown",
            "interests": ["Deep Learning", "Computer Vision"],
            "publications": [
                {"title": "ImageNet classification",
                 "abstract": "Deep convolutional neural networks for image recognition.",
                 "year": 2015,
                 "authors": [103, 101, 107]},
                {"title": "ResNet architecture", "abstract": "Deep residual learning for image recognition.",
                 "year": 2016,
                 "authors": [103, 440]}
            ]
        }
    },
    104: {
        "combined": {
            "name": "Dr. Elena Rodriguez",
            "interests": ["Quantum Physics", "Superconductivity", "Particle Physics"],
            "publications": [
                {"title": "Quantum entanglement in macroscopic systems",
                 "abstract": "Exploring non-local correlations in large-scale quantum networks.",
                 "year": 2021,
                 "authors": [104, 111, 905]},
                {"title": "High-temperature superconductivity",
                 "abstract": "New materials for lossless energy transmission at liquid nitrogen temperatures.",
                 "year": 2018,
                 "authors": [104, 305, 306]}
            ]
        }
    },
    105: {
        "combined": {
            "name": "Prof. Arthur Hamilton",
            "interests": ["Medieval History", "Feudalism", "European Warfare"],
            "publications": [
                {"title": "The economics of the Hundred Years' War",
                 "abstract": "An analysis of trade routes and currency devaluation during the conflict.",
                 "year": 2019,
                 "authors": [105, 201]},
                {"title": "Knights and Castles: A structural analysis",
                 "abstract": "Evolution of fortification techniques in the 13th century.",
                 "year": 2015,
                 "authors": [105, 202, 114]}
            ]
        }
    },
    106: {
        "combined": {
            "name": "Sarah Connor",
            "interests": ["Cybersecurity", "Network Security", "Cryptography"],
            "publications": [
                {"title": "Zero-day exploit detection",
                 "abstract": "Using anomaly detection to identify unknown vulnerabilities in real-time.",
                 "year": 2022,
                 "authors": [106, 112, 500]},
                {"title": "Blockchain for secure voting",
                 "abstract": "A decentralized ledger approach to election integrity.",
                 "year": 2021,
                 "authors": [106, 501, 502, 503]}
            ]
        }
    },
    107: {
        "combined": {
            "name": "Dr. Hiroshi Tanaka",
            "interests": ["Robotics", "Control Theory", "Human-Robot Interaction"],
            "publications": [
                {"title": "Soft robotics manipulation",
                 "abstract": "Grasping fragile objects using pneumatic artificial muscles.",
                 "year": 2020,
                 "authors": [107, 103, 610]},
                {"title": "Swarm intelligence in drones",
                 "abstract": "Coordinated flight patterns for search and rescue operations.",
                 "year": 2023,
                 "authors": [107, 611]}
            ]
        }
    },
    108: {
        "combined": {
            "name": "Prof. Emily Brontë",
            "interests": ["Literature", "Victorian Era", "Poetry"],
            "publications": [
                {"title": "Gothic elements in 19th-century fiction",
                 "abstract": "The role of setting and atmosphere in classic horror novels.",
                 "year": 2016,
                 "authors": [108, 250]},
                {"title": "Symbolism in romantic poetry",
                 "abstract": "Nature as a metaphor for human emotion.",
                 "year": 2018,
                 "authors": [108, 251, 105]}
            ]
        }
    },
    109: {
        "combined": {
            "name": "Dr. Raj Patel",
            "interests": ["Macroeconomics", "Fiscal Policy", "Inflation"],
            "publications": [
                {"title": "Global supply chain disruptions",
                 "abstract": "Impact of post-pandemic logistics on global inflation rates.",
                 "year": 2022,
                 "authors": [109, 106, 750]},
                {"title": "Cryptocurrency and central banks",
                 "abstract": "The threat and opportunity of digital currencies for national monetary policy.",
                 "year": 2021,
                 "authors": [109, 751]}
            ]
        }
    },
    110: {
        "combined": {
            "name": "Dr. Lisa Cuddy",
            "interests": ["Neuroscience", "Cognitive Science", "Memory"],
            "publications": [
                {"title": "Plasticity in the aging brain",
                 "abstract": "Mechanisms of synaptic adaptation in elderly patients.",
                 "year": 2019,
                 "authors": [110, 113, 800]},
                {"title": "fMRI studies of decision making",
                 "abstract": "Mapping the prefrontal cortex activity during high-stakes gambling tasks.",
                 "year": 2020,
                 "authors": [110, 109, 801, 802]}
            ]
        }
    },
    111: {
        "combined": {
            "name": "Prof. Sheldon Cooper",
            "interests": ["String Theory", "Theoretical Physics", "Cosmology"],
            "publications": [
                {"title": "M-Theory and dark matter",
                 "abstract": "Unifying gravity with quantum mechanics in 11 dimensions.",
                 "year": 2018,
                 "authors": [111, 104, 115]},
                {"title": "Black hole thermodynamics",
                 "abstract": "Information paradox and Hawking radiation revisited.",
                 "year": 2017,
                 "authors": [111, 900]}
            ]
        }
    },
    112: {
        "combined": {
            "name": "Grace Hopper",
            "interests": ["Compilers", "Programming Languages", "Legacy Systems"],
            "publications": [
                {"title": "Optimizing COBOL for modern cloud",
                 "abstract": "Strategies for migrating mainframe codebases to microservices.",
                 "year": 2023,
                 "authors": [112, 106]},
                {"title": "Static analysis of functional code",
                 "abstract": "Type inference algorithms for safe memory management.",
                 "year": 2020,
                 "authors": [112, 101, 950]}
            ]
        }
    },
    113: {
        "combined": {
            "name": "Dr. Julian Bashir",
            "interests": ["Immunology", "Virology", "Epidemiology"],
            "publications": [
                {"title": "mRNA vaccine efficacy",
                 "abstract": "Long-term study of immune response to spike proteins.",
                 "year": 2021,
                 "authors": [113, 102, 330]},
                {"title": "Vector-borne diseases in tropical climates",
                 "abstract": "Predictive modeling of malaria spread based on climate change patterns.",
                 "year": 2019,
                 "authors": [113, 110, 331]}
            ]
        }
    },
    114: {
        "combined": {
            "name": "Prof. Indiana Jones",
            "interests": ["Archaeology", "Anthropology", "Ancient Civilizations"],
            "publications": [
                {"title": "Lost temples of the Amazon",
                 "abstract": "LiDAR mapping reveals hidden structures under the canopy.",
                 "year": 2017,
                 "authors": [114, 105, 450]},
                {"title": "Ceramics of the Ming Dynasty",
                 "abstract": "Chemical analysis of glazes used in 15th-century porcelain.",
                 "year": 2015,
                 "authors": [114, 451]}
            ]
        }
    },
    115: {
        "combined": {
            "name": "Dr. Neil Tyson",
            "interests": ["Astronomy", "Exoplanets", "Astrophysics"],
            "publications": [
                {"title": "Spectroscopy of distant atmospheres",
                 "abstract": "Detecting biosignatures on planets in the habitable zone.",
                 "year": 2022,
                 "authors": [115, 111, 102]},
                {"title": "The expansion rate of the universe",
                 "abstract": "Resolving the tension in Hubble constant measurements.",
                 "year": 2020,
                 "authors": [115, 555]}
            ]
        }
    }
}

recsys = RecSys(users_data, gemini_api_key='AIzaSyBWHPrr6iIibCN9qNN4YCiaZ0pbjkRHnsk')
result = recsys.recommend(115, 'I want to do cybersecurity research focusing on network defense strategies.', top_n=3)
print(result)
# # 2. Инициализация движка
# engine = AuthorSearchEngine()
#
# # 3. Индексация данных
# engine.process_and_index(users_data)

# print("\n--- Тест 1: Поиск похожих на Alice (ID 101) ---")
# # Alice занимается NLP. Ближе всего к ней должен быть Charlie (Deep Learning), а не Bob (Biology).
# similar_users = engine.search_similar_to_author(101, top_k=2)
# for u in similar_users:
#     print(f"ID: {u['id']}, Name: {u['name']}, Score: {u['score']:.4f}, Interests: {u['interests']}")
#
# print("\n--- Тест 2: Поиск по текстовому запросу ---")
# query = "I need someone who knows about DNA and genes"
# results = engine.search_by_text(query, top_k=1)
# for u in results:
#     print(f"Запрос: '{query}' -> Найдено: {u['name']} (Score: {u['score']:.4f})")


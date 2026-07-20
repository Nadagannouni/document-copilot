from functools import lru_cache
from pathlib import Path
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parent.parent #avant ca on a un erreur (ValidationError ) car dans le settings on n a pas mis le chemin du fichier .env (ca etait ".env") donc pydantic ne trouvait pas le fichier .env et donc il n arrivait pas a charger les variables d environnement. Donc on a mis le chemin du fichier .env pour que pydantic puisse le trouver et charger les variables d environnement correctement. Donc on a mis _BACKEND_DIR = Path(__file__).resolve().parent.parent pour que pydantic puisse trouver le fichier .env et charger les variables d environnement correctement.
#and our app can now imprt settings from app.config import settings .
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR
        / ".env",  # here we're linking to where the .env file is located. so be sure of the path. If the .env file is in the root of the project, this is fine. If it's in a different directory, you need to adjust the path accordingly.
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = Field(
        alias="SUPABASE_URL"
    )  # hne zeyda hal field car pydantic cherche automatiquement les variables d'environnement correspondantes car il le convertit en majuscule et remplace les points par des underscores. Donc si vous avez une variable d'environnement SUPABASE_URL, elle sera automatiquement mappée à ce champ.
    supabase_anon_key: str = Field(alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")

    database_url: PostgresDsn = Field(
        alias="DATABASE_URL"
    )  # ici il n a pas mis str, il a mis PostgresDsn, c est un type de pydantic qui valide que la valeur est une URL de base de données PostgreSQL valide. Cela permet de s'assurer que la chaîne de connexion fournie est correcte et peut être utilisée pour se connecter à la base de données.

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        alias="OPENAI_EMBEDDING_MODEL"
    )  # pas de valeur par défaut donc Si une variable manque : ValidationError  au démarrage.Lequel est meilleur ?Ça dépend. En production on préfère souvent que l'application refuse de démarrer plutôt que d'utiliser une mauvaise configuration. donc pour la production, cette methode de ne pas mettre de valeur par défaut est préférable. Pour le développement, on peut mettre une valeur par défaut pour faciliter les tests.
    openai_embedding_dimensions: int = Field(alias="OPENAI_EMBEDDING_DIMENSIONS")

    allowed_origins_csv: str = Field(alias="ALLOWED_ORIGINS")

    # @computed_field avec ca La propriété devient un vrai champ Pydantic.
    #     @property
    # settings.model_dump() renverra {
    #    ...
    #    "cors_origins":[...]
    # }
    # c est pas indisponsable mais C'est utile lorsqu'on veut sérialiser ou exposer cette valeur.

    @property
    def allowed_origins(self) -> list[str]:
        origins = [
            origin.strip()
            for origin in self.allowed_origins_csv.split(",")
            if origin.strip()
        ]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must include at least one origin")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ca peut etre juste settings = Settings() mais avec lru_cache, on s'assure que la configuration est chargée une seule fois et réutilisée partout dans l'application. Cela peut améliorer les performances et éviter de relire le fichier .env plusieurs fois.

settings = get_settings()

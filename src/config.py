"""Configuration management for the application"""
import os
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    url: str = Field(default="postgresql://user:password@localhost:5432/rag_db")
    vector_dimension: int = Field(default=1536)
    
    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class Neo4jConfig(BaseSettings):
    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: str = Field(default="")
    
    model_config = SettingsConfigDict(env_prefix="NEO4J_")


class LLMConfig(BaseSettings):
    provider: Literal["ollama", "openai", "gemini", "openrouter"] = Field(default="ollama")
    base_url: str = Field(default="http://localhost:11434/v1")
    api_key: str = Field(default="ollama")
    choice: str = Field(default="llama3.2:latest")
    
    model_config = SettingsConfigDict(env_prefix="LLM_")


class EmbeddingConfig(BaseSettings):
    provider: Literal["ollama", "openai"] = Field(default="ollama")
    base_url: str = Field(default="http://localhost:11434/v1")
    api_key: str = Field(default="ollama")
    model: str = Field(default="nomic-embed-text")
    
    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")


class OpenAIConfig(BaseSettings):
    api_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="gpt-4o-mini")
    embedding_model: str = Field(default="text-embedding-3-large")
    
    model_config = SettingsConfigDict(env_prefix="OPENAI_")


class GeminiConfig(BaseSettings):
    api_key: Optional[str] = Field(default=None)
    model: str = Field(default="gemini-2.0-flash-exp")
    
    model_config = SettingsConfigDict(env_prefix="GEMINI_")


class AppConfig(BaseSettings):
    env: Literal["development", "production", "test"] = Field(default="development")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    api_port: int = Field(default=8000)
    api_host: str = Field(default="0.0.0.0")
    
    model_config = SettingsConfigDict(env_prefix="APP_")


class DataConfig(BaseSettings):
    data_dir: str = Field(default="./rag-data/data")
    index_dir: str = Field(default="./rag-data/index")
    metadata_db: str = Field(default="./rag-data/metadata.db")
    
    model_config = SettingsConfigDict(env_prefix="")


class ProcessingConfig(BaseSettings):
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    batch_size: int = Field(default=10)
    max_workers: int = Field(default=4)
    request_timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=1)
    
    model_config = SettingsConfigDict(env_prefix="")


class FeatureFlags(BaseSettings):
    enable_graph_building: bool = Field(default=True)
    enable_watchdog: bool = Field(default=False)
    offline_mode: bool = Field(default=False)
    
    model_config = SettingsConfigDict(env_prefix="")


class Settings(BaseSettings):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


def get_settings() -> Settings:
    return Settings()

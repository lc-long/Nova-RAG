package config

import (
	"os"
)

type Config struct {
	ServerPort  string
	PythonHost string
	PythonPort string
	DBPath     string
	Env        string
}

func Load() *Config {
	return &Config{
		ServerPort:  getEnv("SERVER_PORT", "8080"),
		PythonHost:  getEnv("PYTHON_HOST", "localhost"),
		PythonPort:  getEnv("PYTHON_PORT", "5000"),
		DBPath:      getEnv("DB_PATH", "./lumina.db"),
		Env:         getEnv("ENV", "development"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

package main

import (
	"log"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"lumina-insight/internal/config"
	"lumina-insight/internal/handler"
	"lumina-insight/internal/model"
)

func main() {
	_ = godotenv.Load()

	cfg := config.Load()

	db, err := gorm.Open(sqlite.Open(cfg.DBPath), &gorm.Config{})
	if err != nil {
		log.Fatal("failed to connect database")
	}

	if err := db.AutoMigrate(&model.Document{}); err != nil {
		log.Fatal("failed to migrate database")
	}

	r := gin.Default()

	docsHandler := handler.NewDocsHandler()
	chatHandler := handler.NewChatHandler(cfg.PythonHost, cfg.PythonPort)

	api := r.Group("/api/v1")
	{
		api.POST("/docs/upload", docsHandler.Upload)
		api.GET("/docs", docsHandler.List)
		api.DELETE("/docs/:id", docsHandler.Delete)

		api.POST("/chat/completions", chatHandler.Completions)
	}

	log.Printf("Server starting on port %s", cfg.ServerPort)
	if err := r.Run(":" + cfg.ServerPort); err != nil {
		log.Fatal("failed to start server")
	}
}

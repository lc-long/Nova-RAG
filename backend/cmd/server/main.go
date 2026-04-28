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
	"lumina-insight/internal/storage"
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

	sqlDB := &storage.Database{DB: db}

	r := gin.Default()

	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	docsHandler := handler.NewDocsHandler(sqlDB, cfg.PythonHost, cfg.PythonPort)
	chatHandler := handler.NewChatHandler(cfg.PythonHost, cfg.PythonPort)
	systemHandler := handler.NewSystemHandler(sqlDB, cfg.PythonHost, cfg.PythonPort)

	api := r.Group("/api/v1")
	{
		api.POST("/docs/upload", docsHandler.Upload)
		api.GET("/docs", docsHandler.List)
		api.DELETE("/docs/:id", docsHandler.Delete)

		api.POST("/chat/completions", chatHandler.Completions)

		api.POST("/system/reset", systemHandler.Reset)
	}

	log.Printf("Server starting on port %s", cfg.ServerPort)
	if err := r.Run(":" + cfg.ServerPort); err != nil {
		log.Fatal("failed to start server")
	}
}

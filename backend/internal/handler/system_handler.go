package handler

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	"lumina-insight/internal/storage"
)

type SystemHandler struct {
	db         *storage.Database
	pythonHost string
	pythonPort string
	uploadDir  string
}

func NewSystemHandler(db *storage.Database, pythonHost, pythonPort string) *SystemHandler {
	return &SystemHandler{
		db:         db,
		pythonHost: pythonHost,
		pythonPort: pythonPort,
		uploadDir:  "./uploads",
	}
}

func (h *SystemHandler) Reset(c *gin.Context) {
	fmt.Println("[SystemHandler] Starting full system reset...")

	// Action A: Clear SQLite documents table
	if err := h.db.DB.Exec("DELETE FROM documents").Error; err != nil {
		fmt.Printf("[SystemHandler] DB delete error: %v\n", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to clear database"})
		return
	}
	fmt.Println("[SystemHandler] SQLite documents table cleared")

	// Action B: Clear upload files
	if err := h.clearUploadDir(); err != nil {
		fmt.Printf("[SystemHandler] Upload dir clear error: %v\n", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to clear uploads"})
		return
	}
	fmt.Println("[SystemHandler] Upload directory cleared")

	// Action C: Trigger Python ChromaDB reset
	pythonURL := fmt.Sprintf("http://127.0.0.1:%s/reset_db", h.pythonPort)
	req, _ := http.NewRequest("POST", pythonURL, bytes.NewBuffer([]byte("{}")))
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		fmt.Printf("[SystemHandler] Python reset error: %v\n", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to reset Python ChromaDB"})
		return
	}
	defer resp.Body.Close()

	bodyBytes, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		fmt.Printf("[SystemHandler] Python reset failed [%d]: %s\n", resp.StatusCode, string(bodyBytes))
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("python reset failed: %s", string(bodyBytes))})
		return
	}
	fmt.Printf("[SystemHandler] Python ChromaDB reset: %s\n", string(bodyBytes))

	fmt.Println("[SystemHandler] Full system reset complete")
	c.JSON(http.StatusOK, gin.H{"message": "System reset complete"})
}

func (h *SystemHandler) clearUploadDir() error {
	entries, err := os.ReadDir(h.uploadDir)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		fullPath := filepath.Join(h.uploadDir, entry.Name())
		if err := os.Remove(fullPath); err != nil {
			return err
		}
	}
	return nil
}
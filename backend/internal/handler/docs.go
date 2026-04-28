package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"lumina-insight/internal/model"
	"lumina-insight/internal/storage"
)

type DocsHandler struct {
	uploadDir string
	db        *storage.Database
	pythonHost string
	pythonPort string
}

func NewDocsHandler(db *storage.Database, pythonHost, pythonPort string) *DocsHandler {
	dir := "./uploads"
	os.MkdirAll(dir, 0755)
	return &DocsHandler{
		uploadDir: dir,
		db:        db,
		pythonHost: pythonHost,
		pythonPort: pythonPort,
	}
}

type UploadResponse struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Size        int64  `json:"size"`
	ChunksCount int    `json:"chunks_count"`
	Status      string `json:"status"`
}

func (h *DocsHandler) Upload(c *gin.Context) {
	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "no file provided"})
		return
	}
	defer file.Close()

	docID := fmt.Sprintf("%d", os.Getpid()) + "-" + strconv.FormatInt(time.Now().UnixNano(), 36)
	savedPath := filepath.Join(h.uploadDir, docID+"_"+header.Filename)

	out, err := os.Create(savedPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to save file"})
		return
	}
	defer out.Close()

	size, err := io.Copy(out, file)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to write file"})
		return
	}

	doc := &model.Document{
		ID:     docID,
		Name:   header.Filename,
		Size:   size,
		Status: "processing",
	}
	h.db.DB.Create(doc)

	go h.ingestToPython(docID, header.Filename, savedPath)

	c.JSON(http.StatusCreated, UploadResponse{
		ID:     docID,
		Name:   header.Filename,
		Size:   size,
		Status: "processing",
	})
}

func (h *DocsHandler) ingestToPython(docID, filename, filePath string) {
	url := fmt.Sprintf("http://%s:%s/ingest", h.pythonHost, h.pythonPort)

	payload := map[string]string{
		"doc_id":   docID,
		"filename": filename,
		"file_path": filePath,
	}
	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Doc-ID", docID)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		fmt.Printf("[DocsHandler] Ingest failed for %s: %v\n", filename, err)
		h.db.DB.Model(&model.Document{}).Where("id = ?", docID).Update("status", "failed")
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var result map[string]interface{}
		json.NewDecoder(resp.Body).Decode(&result)
		chunks := 0
		if n, ok := result["chunks"].(float64); ok {
			chunks = int(n)
		}
		h.db.DB.Model(&model.Document{}).Where("id = ?", docID).Updates(map[string]interface{}{
			"status": "ready",
		})
		fmt.Printf("[DocsHandler] Ingested %s: %d chunks\n", filename, chunks)
	} else {
		h.db.DB.Model(&model.Document{}).Where("id = ?", docID).Update("status", "failed")
		fmt.Printf("[DocsHandler] Ingest failed for %s: status %d\n", filename, resp.StatusCode)
	}
}

func (h *DocsHandler) List(c *gin.Context) {
	var docs []model.Document
	h.db.DB.Order("created_at desc").Find(&docs)
	c.JSON(http.StatusOK, docs)
}

func (h *DocsHandler) Delete(c *gin.Context) {
	id := c.Param("id")
	var doc model.Document
	if h.db.DB.First(&doc, "id = ?", id).Error != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	h.db.DB.Delete(&doc)
	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}
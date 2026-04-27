package handler

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

type ChatHandler struct {
	pythonHost string
	pythonPort string
}

func NewChatHandler(pythonHost, pythonPort string) *ChatHandler {
	return &ChatHandler{
		pythonHost: pythonHost,
		pythonPort: pythonPort,
	}
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type QueryRequest struct {
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream"`
}

func (h *ChatHandler) Completions(c *gin.Context) {
	var req QueryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}

	url := fmt.Sprintf("http://%s:%s/process_query", h.pythonHost, h.pythonPort)
	jsonBody, _ := json.Marshal(req)

	httpReq, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create request"})
		return
	}
	httpReq.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(httpReq)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to call python service: %v", err)})
		return
	}
	defer resp.Body.Close()

	c.Writer.Header().Set("Content-Type", "text/event-stream")
	c.Writer.Header().Set("Cache-Control", "no-cache")
	c.Writer.Header().Set("Connection", "keep-alive")
	c.Writer.Header().Set("X-Accel-Buffering", "no")

	flusher, ok := c.Writer.(http.Flusher)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "streaming not supported"})
		return
	}

	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		if _, err := c.Writer.WriteString(line + "\n"); err == nil {
			flusher.Flush()
		}
		fmt.Printf("[ChatHandler] SSE line: %s\n", line)
	}
	if err := scanner.Err(); err != nil {
		fmt.Printf("[ChatHandler] Scan error: %v\n", err)
	}
}
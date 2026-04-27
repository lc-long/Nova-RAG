package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type ChatHandler struct{}

func NewChatHandler() *ChatHandler {
	return &ChatHandler{}
}

func (h *ChatHandler) Completions(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "stub"})
}

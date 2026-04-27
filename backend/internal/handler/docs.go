package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type DocsHandler struct{}

func NewDocsHandler() *DocsHandler {
	return &DocsHandler{}
}

func (h *DocsHandler) Upload(c *gin.Context) {
	c.JSON(http.StatusCreated, gin.H{"status": "stub"})
}

func (h *DocsHandler) List(c *gin.Context) {
	c.JSON(http.StatusOK, []gin.H{})
}

func (h *DocsHandler) Delete(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "stub"})
}

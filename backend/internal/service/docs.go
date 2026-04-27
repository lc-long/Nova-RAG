package service

import (
	"github.com/google/uuid"
	"gorm.io/gorm"
	"lumina-insight/internal/model"
)

type DocsService struct {
	db *gorm.DB
}

func NewDocsService(db *gorm.DB) *DocsService {
	return &DocsService{db: db}
}

func (s *DocsService) CreateDocument(name string, size int64) (*model.Document, error) {
	doc := &model.Document{
		ID:     uuid.New().String(),
		Name:   name,
		Size:   size,
		Status: "processing",
	}
	if err := s.db.Create(doc).Error; err != nil {
		return nil, err
	}
	return doc, nil
}

func (s *DocsService) ListDocuments() ([]model.Document, error) {
	var docs []model.Document
	if err := s.db.Find(&docs).Error; err != nil {
		return nil, err
	}
	return docs, nil
}

func (s *DocsService) DeleteDocument(id string) error {
	return s.db.Delete(&model.Document{}, "id = ?", id).Error
}

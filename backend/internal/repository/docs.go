package repository

import (
	"lumina-insight/internal/model"

	"gorm.io/gorm"
)

type DocsRepository struct {
	db *gorm.DB
}

func NewDocsRepository(db *gorm.DB) *DocsRepository {
	return &DocsRepository{db: db}
}

func (r *DocsRepository) Create(doc *model.Document) error {
	return r.db.Create(doc).Error
}

func (r *DocsRepository) FindAll() ([]model.Document, error) {
	var docs []model.Document
	if err := r.db.Find(&docs).Error; err != nil {
		return nil, err
	}
	return docs, nil
}

func (r *DocsRepository) Delete(id string) error {
	return r.db.Delete(&model.Document{}, "id = ?", id).Error
}

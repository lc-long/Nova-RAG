package model

import (
	"time"
)

type Document struct {
	ID        string    `gorm:"primaryKey;type:varchar(36)" json:"id"`
	Name      string    `gorm:"type:varchar(255)" json:"name"`
	Size      int64     `json:"size"`
	Status    string    `gorm:"type:varchar(50)" json:"status"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

func (Document) TableName() string {
	return "documents"
}

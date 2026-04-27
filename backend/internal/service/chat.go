package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
)

type ChatService struct {
	pythonHost string
	pythonPort string
}

func NewChatService(host, port string) *ChatService {
	return &ChatService{
		pythonHost: host,
		pythonPort: port,
	}
}

type QueryRequest struct {
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream"`
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

func (s *ChatService) ProcessQuery(messages []Message, stream bool) (*http.Response, error) {
	url := fmt.Sprintf("http://%s:%s/process_query", s.pythonHost, s.pythonPort)
	body := QueryRequest{Messages: messages, Stream: stream}
	jsonBody, _ := json.Marshal(body)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonBody))
	return resp, err
}

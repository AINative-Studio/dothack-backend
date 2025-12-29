package events

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"leaderboard/leaderboard"
	"leaderboard/websocket"
)

// Event represents a ZeroDB event
type Event struct {
	ID          string                 `json:"id"`
	Type        string                 `json:"event_type"`
	Source      string                 `json:"source"`
	Data        map[string]interface{} `json:"event_data"`
	CreatedAt   time.Time              `json:"created_at"`
}

// Subscriber handles event stream subscription
type Subscriber struct {
	apiKey      string
	projectID   string
	baseURL     string
	calculator  *leaderboard.Calculator
	hub         *websocket.Hub
	httpClient  *http.Client
}

// NewSubscriber creates a new event subscriber
func NewSubscriber(apiKey, projectID, baseURL string, calculator *leaderboard.Calculator, hub *websocket.Hub) *Subscriber {
	return &Subscriber{
		apiKey:     apiKey,
		projectID:  projectID,
		baseURL:    baseURL,
		calculator: calculator,
		hub:        hub,
		httpClient: &http.Client{
			Timeout: 0, // No timeout for SSE connections
		},
	}
}

// Subscribe connects to the event stream and processes events
func (s *Subscriber) Subscribe(ctx context.Context) error {
	eventTypes := []string{"score.submitted", "submission.created"}

	for {
		select {
		case <-ctx.Done():
			log.Println("Event subscription cancelled")
			return ctx.Err()
		default:
			if err := s.subscribeWithRetry(ctx, eventTypes); err != nil {
				log.Printf("Subscription error: %v, retrying in 5 seconds...", err)
				time.Sleep(5 * time.Second)
			}
		}
	}
}

// subscribeWithRetry attempts to subscribe with automatic retry
func (s *Subscriber) subscribeWithRetry(ctx context.Context, eventTypes []string) error {
	url := fmt.Sprintf("%s/v1/public/projects/%s/database/events/subscribe",
		s.baseURL, s.projectID)

	payload := map[string]interface{}{
		"event_types": eventTypes,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("Authorization", "Bearer "+s.apiKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("subscription failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	log.Printf("Connected to event stream, listening for: %v", eventTypes)

	// Read SSE stream
	reader := bufio.NewReader(resp.Body)
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			line, err := reader.ReadBytes('\n')
			if err != nil {
				if err == io.EOF {
					log.Println("Event stream closed by server")
					return nil
				}
				return fmt.Errorf("error reading event stream: %w", err)
			}

			// Parse SSE format
			if len(line) > 6 && string(line[:6]) == "data: " {
				eventData := line[6:]
				s.handleEvent(eventData)
			}
		}
	}
}

// handleEvent processes incoming events
func (s *Subscriber) handleEvent(data []byte) {
	var event Event
	if err := json.Unmarshal(data, &event); err != nil {
		log.Printf("Error parsing event: %v", err)
		return
	}

	log.Printf("Received event: type=%s, id=%s", event.Type, event.ID)

	// Extract hackathon ID from event data
	hackathonID, ok := event.Data["hackathon_id"].(string)
	if !ok {
		log.Printf("Event missing hackathon_id: %+v", event.Data)
		return
	}

	// Process based on event type
	switch event.Type {
	case "score.submitted":
		s.handleScoreSubmitted(hackathonID, event)
	case "submission.created":
		s.handleSubmissionCreated(hackathonID, event)
	default:
		log.Printf("Unknown event type: %s", event.Type)
	}
}

// handleScoreSubmitted processes score submission events
func (s *Subscriber) handleScoreSubmitted(hackathonID string, event Event) {
	log.Printf("Processing score submission for hackathon %s", hackathonID)

	// Invalidate cache to force fresh calculation
	s.calculator.InvalidateCache(hackathonID)

	// Calculate updated leaderboard
	rankings, err := s.calculator.CalculateLeaderboard(hackathonID)
	if err != nil {
		log.Printf("Error calculating leaderboard: %v", err)
		return
	}

	// Broadcast update to all connected clients
	s.broadcastUpdate(hackathonID, rankings)
}

// handleSubmissionCreated processes new submission events
func (s *Subscriber) handleSubmissionCreated(hackathonID string, event Event) {
	log.Printf("Processing new submission for hackathon %s", hackathonID)

	// Invalidate cache to force fresh calculation
	s.calculator.InvalidateCache(hackathonID)

	// Calculate updated leaderboard
	rankings, err := s.calculator.CalculateLeaderboard(hackathonID)
	if err != nil {
		log.Printf("Error calculating leaderboard: %v", err)
		return
	}

	// Broadcast update to all connected clients
	s.broadcastUpdate(hackathonID, rankings)
}

// broadcastUpdate sends leaderboard updates to WebSocket clients
func (s *Subscriber) broadcastUpdate(hackathonID string, rankings []leaderboard.LeaderboardEntry) {
	message := map[string]interface{}{
		"type":      "leaderboard_update",
		"data":      rankings,
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(message)
	if err != nil {
		log.Printf("Error marshaling leaderboard update: %v", err)
		return
	}

	clientCount := s.hub.GetClientCount(hackathonID)
	log.Printf("Broadcasting leaderboard update to %d clients for hackathon %s", clientCount, hackathonID)

	s.hub.Broadcast(hackathonID, data)
}

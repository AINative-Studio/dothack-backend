package websocket

import (
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"leaderboard/leaderboard"
)

const (
	// Time allowed to write a message to the peer
	writeWait = 10 * time.Second

	// Time allowed to read the next pong message from the peer
	pongWait = 60 * time.Second

	// Send pings to peer with this period (must be less than pongWait)
	pingPeriod = (pongWait * 9) / 10

	// Maximum message size allowed from peer
	maxMessageSize = 512
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		// In production, implement proper origin checking
		return true
	},
}

// Client represents a websocket client connection
type Client struct {
	hub *Hub

	// The websocket connection
	conn *websocket.Conn

	// Buffered channel of outbound messages
	send chan []byte

	// Hackathon ID this client is subscribed to
	hackathonID string
}

// readPump pumps messages from the websocket connection to the hub
func (c *Client) readPump() {
	defer func() {
		c.hub.Unregister(c)
		c.conn.Close()
	}()

	c.conn.SetReadLimit(maxMessageSize)
	c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		c.conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	for {
		_, _, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}
		// Currently, we don't process client messages
		// All communication is server -> client
	}
}

// writePump pumps messages from the hub to the websocket connection
func (c *Client) writePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				// The hub closed the channel
				c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)

			// Add queued messages to the current websocket message
			n := len(c.send)
			for i := 0; i < n; i++ {
				w.Write([]byte{'\n'})
				w.Write(<-c.send)
			}

			if err := w.Close(); err != nil {
				return
			}

		case <-ticker.C:
			c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// ServeWS handles websocket requests from clients
func ServeWS(hub *Hub, calculator *leaderboard.Calculator, w http.ResponseWriter, r *http.Request) {
	// Extract hackathon ID from URL path
	// Expected: /ws/hackathons/{hackathon_id}
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(pathParts) != 3 || pathParts[0] != "ws" || pathParts[1] != "hackathons" {
		http.Error(w, "Invalid path. Use /ws/hackathons/{hackathon_id}", http.StatusBadRequest)
		return
	}

	hackathonID := pathParts[2]
	if hackathonID == "" {
		http.Error(w, "Hackathon ID required", http.StatusBadRequest)
		return
	}

	// Upgrade connection to WebSocket
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	client := &Client{
		hub:         hub,
		conn:        conn,
		send:        make(chan []byte, 256),
		hackathonID: hackathonID,
	}

	client.hub.Register(client)

	// Send initial leaderboard state
	go func() {
		rankings, err := calculator.CalculateLeaderboard(hackathonID)
		if err != nil {
			log.Printf("Error calculating initial leaderboard: %v", err)
			return
		}

		message := map[string]interface{}{
			"type":      "leaderboard_update",
			"data":      rankings,
			"timestamp": time.Now().UTC().Format(time.RFC3339),
		}

		data, err := json.Marshal(message)
		if err != nil {
			log.Printf("Error marshaling initial leaderboard: %v", err)
			return
		}

		select {
		case client.send <- data:
		case <-time.After(5 * time.Second):
			log.Println("Timeout sending initial leaderboard")
		}
	}()

	// Start goroutines for reading and writing
	go client.writePump()
	go client.readPump()
}

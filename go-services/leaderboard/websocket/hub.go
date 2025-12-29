package websocket

import (
	"log"
	"sync"
)

// Hub maintains the set of active clients and broadcasts messages to clients
type Hub struct {
	// Registered clients organized by hackathon ID
	clients map[string]map[*Client]bool

	// Inbound messages from the clients
	broadcast chan *BroadcastMessage

	// Register requests from the clients
	register chan *Client

	// Unregister requests from clients
	unregister chan *Client

	// Mutex for thread-safe access to clients map
	mu sync.RWMutex

	// Shutdown signal
	shutdown chan bool
}

// BroadcastMessage represents a message to broadcast to clients
type BroadcastMessage struct {
	HackathonID string
	Data        []byte
}

// NewHub creates a new Hub instance
func NewHub() *Hub {
	return &Hub{
		broadcast:  make(chan *BroadcastMessage, 256),
		register:   make(chan *Client, 256),
		unregister: make(chan *Client, 256),
		clients:    make(map[string]map[*Client]bool),
		shutdown:   make(chan bool),
	}
}

// Run starts the hub's main event loop
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			if _, exists := h.clients[client.hackathonID]; !exists {
				h.clients[client.hackathonID] = make(map[*Client]bool)
			}
			h.clients[client.hackathonID][client] = true
			h.mu.Unlock()
			log.Printf("Client registered for hackathon %s (total: %d)",
				client.hackathonID, len(h.clients[client.hackathonID]))

		case client := <-h.unregister:
			h.mu.Lock()
			if clients, exists := h.clients[client.hackathonID]; exists {
				if _, ok := clients[client]; ok {
					delete(clients, client)
					close(client.send)
					log.Printf("Client unregistered for hackathon %s (remaining: %d)",
						client.hackathonID, len(clients))

					// Remove empty hackathon map
					if len(clients) == 0 {
						delete(h.clients, client.hackathonID)
					}
				}
			}
			h.mu.Unlock()

		case message := <-h.broadcast:
			h.mu.RLock()
			clients := h.clients[message.HackathonID]
			h.mu.RUnlock()

			// Broadcast to all clients for this hackathon
			for client := range clients {
				select {
				case client.send <- message.Data:
					// Message sent successfully
				default:
					// Client's send channel is full, close it
					h.mu.Lock()
					close(client.send)
					delete(h.clients[message.HackathonID], client)
					h.mu.Unlock()
					log.Printf("Client send buffer full, disconnecting")
				}
			}

		case <-h.shutdown:
			log.Println("Hub shutting down")
			h.mu.Lock()
			for hackathonID, clients := range h.clients {
				for client := range clients {
					close(client.send)
				}
				delete(h.clients, hackathonID)
			}
			h.mu.Unlock()
			return
		}
	}
}

// Broadcast sends a message to all clients subscribed to a specific hackathon
func (h *Hub) Broadcast(hackathonID string, data []byte) {
	select {
	case h.broadcast <- &BroadcastMessage{
		HackathonID: hackathonID,
		Data:        data,
	}:
	default:
		log.Println("Broadcast channel full, dropping message")
	}
}

// Register adds a client to the hub
func (h *Hub) Register(client *Client) {
	h.register <- client
}

// Unregister removes a client from the hub
func (h *Hub) Unregister(client *Client) {
	h.unregister <- client
}

// GetClientCount returns the number of clients for a specific hackathon
func (h *Hub) GetClientCount(hackathonID string) int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	if clients, exists := h.clients[hackathonID]; exists {
		return len(clients)
	}
	return 0
}

// GetTotalClientCount returns the total number of connected clients
func (h *Hub) GetTotalClientCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	total := 0
	for _, clients := range h.clients {
		total += len(clients)
	}
	return total
}

// Shutdown gracefully shuts down the hub
func (h *Hub) Shutdown() {
	close(h.shutdown)
}

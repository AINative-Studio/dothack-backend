package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/joho/godotenv"
	"leaderboard/events"
	"leaderboard/leaderboard"
	"leaderboard/websocket"
)

func main() {
	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using system environment variables")
	}

	// Get configuration
	port := getEnv("GO_EVENT_STREAM_PORT", "9000")
	zeroDBAPIKey := os.Getenv("ZERODB_API_KEY")
	zeroDBProjectID := os.Getenv("ZERODB_PROJECT_ID")
	zeroDBBaseURL := getEnv("ZERODB_BASE_URL", "https://api.ainative.studio")

	if zeroDBAPIKey == "" || zeroDBProjectID == "" {
		log.Fatal("ZERODB_API_KEY and ZERODB_PROJECT_ID must be set")
	}

	// Initialize components
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Create WebSocket hub for managing client connections
	hub := websocket.NewHub()
	go hub.Run()

	// Create leaderboard calculator
	calculator := leaderboard.NewCalculator(zeroDBAPIKey, zeroDBProjectID, zeroDBBaseURL)

	// Create event subscriber
	subscriber := events.NewSubscriber(
		zeroDBAPIKey,
		zeroDBProjectID,
		zeroDBBaseURL,
		calculator,
		hub,
	)

	// Start event subscription in background
	go func() {
		if err := subscriber.Subscribe(ctx); err != nil {
			log.Printf("Error in event subscriber: %v", err)
		}
	}()

	// Setup HTTP routes
	http.HandleFunc("/ws/hackathons/", func(w http.ResponseWriter, r *http.Request) {
		websocket.ServeWS(hub, calculator, w, r)
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"healthy","service":"leaderboard-websocket"}`))
	})

	// Start HTTP server
	server := &http.Server{
		Addr:         fmt.Sprintf(":%s", port),
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown handling
	go func() {
		sigint := make(chan os.Signal, 1)
		signal.Notify(sigint, os.Interrupt, syscall.SIGTERM)
		<-sigint

		log.Println("Shutting down server...")
		cancel() // Cancel context to stop event subscription

		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer shutdownCancel()

		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("Server shutdown error: %v", err)
		}

		hub.Shutdown()
		log.Println("Server stopped")
	}()

	log.Printf("WebSocket server starting on port %s", port)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Server error: %v", err)
	}
}

// getEnv retrieves an environment variable or returns a default value
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

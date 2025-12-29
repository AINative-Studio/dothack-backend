package leaderboard

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sort"
	"sync"
	"time"
)

// Submission represents a hackathon submission
type Submission struct {
	ID          string    `json:"id"`
	HackathonID string    `json:"hackathon_id"`
	TeamID      string    `json:"team_id"`
	TeamName    string    `json:"team_name"`
	TrackID     string    `json:"track_id"`
	TrackName   string    `json:"track_name"`
	ProjectID   string    `json:"project_id"`
	Title       string    `json:"title"`
	SubmittedAt time.Time `json:"submitted_at"`
}

// Score represents a judge's score for a submission
type Score struct {
	ID           string    `json:"id"`
	SubmissionID string    `json:"submission_id"`
	JudgeID      string    `json:"judge_id"`
	Score        float64   `json:"score"`
	CreatedAt    time.Time `json:"created_at"`
}

// LeaderboardEntry represents a single leaderboard entry
type LeaderboardEntry struct {
	Rank         int       `json:"rank"`
	SubmissionID string    `json:"submission_id"`
	TeamID       string    `json:"team_id"`
	TeamName     string    `json:"team_name"`
	TrackID      string    `json:"track_id"`
	TrackName    string    `json:"track_name"`
	Title        string    `json:"title"`
	AverageScore float64   `json:"average_score"`
	ScoreCount   int       `json:"score_count"`
	UpdatedAt    time.Time `json:"updated_at"`
}

// CacheEntry represents a cached leaderboard
type cacheEntry struct {
	rankings  []LeaderboardEntry
	expiresAt time.Time
}

// Calculator handles leaderboard calculation logic
type Calculator struct {
	apiKey      string
	projectID   string
	baseURL     string
	cache       map[string]*cacheEntry
	cacheMutex  sync.RWMutex
	cacheTTL    time.Duration
	httpClient  *http.Client
}

// NewCalculator creates a new Calculator instance
func NewCalculator(apiKey, projectID, baseURL string) *Calculator {
	return &Calculator{
		apiKey:     apiKey,
		projectID:  projectID,
		baseURL:    baseURL,
		cache:      make(map[string]*cacheEntry),
		cacheTTL:   5 * time.Second,
		httpClient: &http.Client{Timeout: 10 * time.Second},
	}
}

// CalculateLeaderboard calculates the leaderboard for a hackathon
func (c *Calculator) CalculateLeaderboard(hackathonID string) ([]LeaderboardEntry, error) {
	// Check cache first
	if rankings := c.getFromCache(hackathonID); rankings != nil {
		return rankings, nil
	}

	// Fetch submissions
	submissions, err := c.fetchSubmissions(hackathonID)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch submissions: %w", err)
	}

	if len(submissions) == 0 {
		return []LeaderboardEntry{}, nil
	}

	// Fetch scores for all submissions
	scores, err := c.fetchScores(hackathonID)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch scores: %w", err)
	}

	// Calculate average scores per submission
	scoreMap := c.calculateAverageScores(scores)

	// Build leaderboard entries
	var rankings []LeaderboardEntry
	for _, submission := range submissions {
		scoreData, hasScores := scoreMap[submission.ID]

		entry := LeaderboardEntry{
			SubmissionID: submission.ID,
			TeamID:       submission.TeamID,
			TeamName:     submission.TeamName,
			TrackID:      submission.TrackID,
			TrackName:    submission.TrackName,
			Title:        submission.Title,
			UpdatedAt:    time.Now().UTC(),
		}

		if hasScores {
			entry.AverageScore = scoreData.average
			entry.ScoreCount = scoreData.count
		}

		rankings = append(rankings, entry)
	}

	// Sort by average score (descending)
	sort.Slice(rankings, func(i, j int) bool {
		// Entries with scores come before entries without scores
		if rankings[i].ScoreCount == 0 && rankings[j].ScoreCount > 0 {
			return false
		}
		if rankings[i].ScoreCount > 0 && rankings[j].ScoreCount == 0 {
			return true
		}
		// If both have scores or both don't, sort by score
		return rankings[i].AverageScore > rankings[j].AverageScore
	})

	// Assign ranks
	for i := range rankings {
		rankings[i].Rank = i + 1
	}

	// Cache the results
	c.setCache(hackathonID, rankings)

	return rankings, nil
}

// InvalidateCache removes a hackathon from the cache
func (c *Calculator) InvalidateCache(hackathonID string) {
	c.cacheMutex.Lock()
	defer c.cacheMutex.Unlock()
	delete(c.cache, hackathonID)
}

// getFromCache retrieves cached leaderboard if not expired
func (c *Calculator) getFromCache(hackathonID string) []LeaderboardEntry {
	c.cacheMutex.RLock()
	defer c.cacheMutex.RUnlock()

	entry, exists := c.cache[hackathonID]
	if !exists || time.Now().After(entry.expiresAt) {
		return nil
	}

	return entry.rankings
}

// setCache stores leaderboard in cache
func (c *Calculator) setCache(hackathonID string, rankings []LeaderboardEntry) {
	c.cacheMutex.Lock()
	defer c.cacheMutex.Unlock()

	c.cache[hackathonID] = &cacheEntry{
		rankings:  rankings,
		expiresAt: time.Now().Add(c.cacheTTL),
	}
}

// fetchSubmissions retrieves all submissions for a hackathon from ZeroDB
func (c *Calculator) fetchSubmissions(hackathonID string) ([]Submission, error) {
	url := fmt.Sprintf("%s/v1/public/projects/%s/database/tables/submissions/query",
		c.baseURL, c.projectID)

	filter := map[string]interface{}{
		"filter": map[string]interface{}{
			"hackathon_id": hackathonID,
		},
	}

	body, err := json.Marshal(filter)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", url, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var result struct {
		Rows []Submission `json:"rows"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result.Rows, nil
}

// fetchScores retrieves all scores for a hackathon from ZeroDB
func (c *Calculator) fetchScores(hackathonID string) ([]Score, error) {
	url := fmt.Sprintf("%s/v1/public/projects/%s/database/tables/scores/query",
		c.baseURL, c.projectID)

	// First, get all submission IDs for this hackathon
	submissions, err := c.fetchSubmissions(hackathonID)
	if err != nil {
		return nil, err
	}

	if len(submissions) == 0 {
		return []Score{}, nil
	}

	// Build list of submission IDs
	submissionIDs := make([]string, len(submissions))
	for i, sub := range submissions {
		submissionIDs[i] = sub.ID
	}

	filter := map[string]interface{}{
		"filter": map[string]interface{}{
			"submission_id": map[string]interface{}{
				"$in": submissionIDs,
			},
		},
	}

	body, err := json.Marshal(filter)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", url, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	var result struct {
		Rows []Score `json:"rows"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result.Rows, nil
}

// scoreData holds aggregated score information
type scoreData struct {
	total   float64
	count   int
	average float64
}

// calculateAverageScores computes average score per submission
func (c *Calculator) calculateAverageScores(scores []Score) map[string]scoreData {
	scoreMap := make(map[string]scoreData)

	for _, score := range scores {
		data := scoreMap[score.SubmissionID]
		data.total += score.Score
		data.count++
		scoreMap[score.SubmissionID] = data
	}

	// Calculate averages
	for submissionID, data := range scoreMap {
		if data.count > 0 {
			data.average = data.total / float64(data.count)
			scoreMap[submissionID] = data
		}
	}

	return scoreMap
}

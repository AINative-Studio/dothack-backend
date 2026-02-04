-- Projects Table Schema for Hackathon Project Management
-- Issue #64: Implement Projects API for Hackathon Project Management
--
-- This table stores hackathon projects submitted by teams.
-- Enforces one project per team per hackathon constraint.

CREATE TABLE IF NOT EXISTS projects (
    -- Primary identifier
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys
    hackathon_id UUID NOT NULL,
    team_id UUID NOT NULL,

    -- Project details
    title VARCHAR(200) NOT NULL,
    one_liner VARCHAR(300),
    description TEXT,

    -- Project status (IDEA, BUILDING, SUBMITTED)
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA',

    -- Project URLs
    repo_url VARCHAR(500),
    demo_url VARCHAR(500),
    video_url VARCHAR(500),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT projects_hackathon_id_fk FOREIGN KEY (hackathon_id)
        REFERENCES hackathons(hackathon_id) ON DELETE CASCADE,
    CONSTRAINT projects_team_id_fk FOREIGN KEY (team_id)
        REFERENCES teams(team_id) ON DELETE CASCADE,
    CONSTRAINT projects_status_check CHECK (status IN ('IDEA', 'BUILDING', 'SUBMITTED')),
    CONSTRAINT projects_unique_team_hackathon UNIQUE (hackathon_id, team_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_hackathon_id ON projects(hackathon_id);
CREATE INDEX IF NOT EXISTS idx_projects_team_id ON projects(team_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_projects_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER projects_updated_at_trigger
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_projects_updated_at();

-- Comments for documentation
COMMENT ON TABLE projects IS 'Hackathon projects submitted by teams';
COMMENT ON COLUMN projects.project_id IS 'Unique project identifier';
COMMENT ON COLUMN projects.hackathon_id IS 'Reference to hackathons table';
COMMENT ON COLUMN projects.team_id IS 'Reference to teams table';
COMMENT ON COLUMN projects.title IS 'Project title (required)';
COMMENT ON COLUMN projects.one_liner IS 'Short project description (300 chars max)';
COMMENT ON COLUMN projects.description IS 'Detailed project description';
COMMENT ON COLUMN projects.status IS 'Project status: IDEA, BUILDING, or SUBMITTED';
COMMENT ON COLUMN projects.repo_url IS 'Repository URL (GitHub, GitLab, etc.)';
COMMENT ON COLUMN projects.demo_url IS 'Live demo or deployment URL';
COMMENT ON COLUMN projects.video_url IS 'Demo video URL (YouTube, Vimeo, etc.)';
COMMENT ON COLUMN projects.created_at IS 'Timestamp when project was created';
COMMENT ON COLUMN projects.updated_at IS 'Timestamp when project was last updated';

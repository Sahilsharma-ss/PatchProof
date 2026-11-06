
import { useEffect, useState } from "react";

import {
  ShieldCheck,
  GitPullRequest,
  Code2,
  Search,
  RefreshCw,
  Lock,
  Globe,
  GitBranch,
  Download,
  LogOut,
  FolderGit2,
  AlertCircle,
  CheckCircle2
} from "lucide-react";

import "./styles.css";

const API_URL = "http://localhost:8000";

// GitHub logo
function GithubLogo({ size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.55.1.76-.24.76-.54v-2.1c-3.1.67-3.76-1.32-3.76-1.32-.5-1.28-1.23-1.62-1.23-1.62-1.01-.69.08-.68.08-.68 1.12.08 1.71 1.15 1.71 1.15.99 1.7 2.59 1.21 3.22.92.1-.72.39-1.21.7-1.49-2.48-.28-5.09-1.24-5.09-5.52 0-1.22.44-2.22 1.15-3-.12-.28-.5-1.42.11-2.95 0 0 .94-.3 3.05 1.15a10.6 10.6 0 0 1 5.55 0c2.11-1.45 3.05-1.15 3.05-1.15.61 1.53.23 2.67.11 2.95.72.78 1.15 1.78 1.15 3 0 4.29-2.62 5.23-5.11 5.51.4.35.75 1.02.75 2.06v3.04c0 .3.2.65.77.54A11.1 11.1 0 0 0 12 .9Z" />
    </svg>
  );
}

// Landing page
function LandingPage() {
  const handleLogin = () => {
    window.location.href = `${API_URL}/api/auth/github/login`;
  };

  return (
    <div className="app">
      <nav className="navbar">
        <div className="logo">
          <Code2 size={25} />
          <span>PR Sentinel</span>
        </div>

        <div className="nav-right">
          AI Code Intelligence
        </div>
      </nav>

      <main className="hero">
        <div className="tag">
          <ShieldCheck size={15} />
          AI POWERED CODE VERIFICATION
        </div>

        <h1>
          Review Code Smarter.
          <br />
          <span>Ship With Confidence.</span>
        </h1>

        <p className="description">
          Connect your GitHub repository and let PR Sentinel
          prepare your codebase for intelligent pull request
          verification, security analysis and regression detection.
        </p>

        <button
          className="github-button"
          onClick={handleLogin}
        >
          <GithubLogo size={20} />
          Continue with GitHub
        </button>

        <div className="features">
          <div className="feature">
            <GitPullRequest size={24} />
            <h3>PR Analysis</h3>
            <p>Understand changes across your repository.</p>
          </div>

          <div className="feature">
            <Code2 size={24} />
            <h3>Code Intelligence</h3>
            <p>Build a structured understanding of your codebase.</p>
          </div>

          <div className="feature">
            <ShieldCheck size={24} />
            <h3>Automated Verification</h3>
            <p>Identify potential issues before merging.</p>
          </div>
        </div>
      </main>
    </div>
  );
}

// Repository dashboard
function Dashboard() {
  const [user, setUser] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cloning, setCloning] = useState(false);
  const [cloneMessage, setCloneMessage] = useState("");

  // Fetch logged-in user and accessible repositories.
  const loadDashboard = async () => {
    setLoading(true);
    setError("");

    try {
      const userResponse = await fetch(`${API_URL}/api/auth/me`, {
        credentials: "include"
      });

      if (userResponse.status === 401) {
        window.location.href = "/";
        return;
      }

      if (!userResponse.ok) {
        throw new Error("Unable to verify your GitHub session.");
      }

      const userData = await userResponse.json();
      setUser(userData.user);

      const repoResponse = await fetch(
        `${API_URL}/api/repositories`,
        {
          credentials: "include"
        }
      );

      if (!repoResponse.ok) {
        const data = await repoResponse.json().catch(() => ({}));
        throw new Error(
          data.detail || "Unable to fetch repositories."
        );
      }

      const repoData = await repoResponse.json();

      setRepositories(repoData.repositories || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  // Clone selected repository.
  const handleClone = async () => {
    if (!selectedRepo) return;

    setCloning(true);
    setCloneMessage("");
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/repositories/${selectedRepo.id}/clone`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          }
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Repository cloning failed.");
      }

      setCloneMessage(
        `Successfully cloned ${selectedRepo.full_name || selectedRepo.name}.`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setCloning(false);
    }
  };

  const handleLogout = async () => {
    await fetch(`${API_URL}/api/auth/logout`, {
      method: "POST",
      credentials: "include"
    });

    window.location.href = "/";
  };

  const filteredRepositories = repositories.filter((repo) => {
    const query = search.toLowerCase();

    return (
      repo.name?.toLowerCase().includes(query) ||
      repo.full_name?.toLowerCase().includes(query) ||
      repo.description?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="dashboard">
      <nav className="navbar">
        <div className="logo">
          <Code2 size={25} />
          <span>PR Sentinel</span>
        </div>

        <div className="dashboard-nav-right">
          {user && (
            <div className="user-info">
              {user.avatar_url && (
                <img
                  src={user.avatar_url}
                  alt="Profile"
                  className="avatar"
                />
              )}
              <span>{user.login}</span>
            </div>
          )}

          <button className="logout-button" onClick={handleLogout}>
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </nav>

      <main className="dashboard-content">
        <div className="dashboard-heading">
          <div>
            <div className="tag">
              <GithubLogo size={15} />
              GITHUB CONNECTED
            </div>

            <h1>Select Your Repository</h1>

            <p>
              Choose a repository to connect it with PR Sentinel.
              We'll clone it into your local workspace for analysis.
            </p>
          </div>

          <button
            className="refresh-button"
            onClick={loadDashboard}
            disabled={loading}
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="message error-message">
            <AlertCircle size={18} />
            {error}
          </div>
        )}

        {cloneMessage && (
          <div className="message success-message">
            <CheckCircle2 size={18} />
            {cloneMessage}
          </div>
        )}

        <div className="repository-panel">
          <div className="repository-panel-heading">
            <div>
              <h2>Your Repositories</h2>
              <p>
                {repositories.length} repositories available
              </p>
            </div>
          </div>

          <div className="search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {loading ? (
            <div className="loading-state">
              <RefreshCw className="spin" size={28} />
              <p>Fetching your GitHub repositories...</p>
            </div>
          ) : repositories.length === 0 && !error ? (
            <div className="empty-state">
              <FolderGit2 size={40} />
              <h3>No accessible repositories found</h3>
              <p>
                Install PatchProof on your GitHub account and grant
                it access to at least one repository.
              </p>
            </div>
          ) : filteredRepositories.length === 0 && !error ? (
            <div className="empty-state">
              <Search size={32} />
              <p>No repositories match your search.</p>
            </div>
          ) : (
            <div className="repository-list">
              {filteredRepositories.map((repo) => (
                <div
                  key={repo.id}
                  className={`repository-card ${
                    selectedRepo?.id === repo.id ? "selected" : ""
                  }`}
                  onClick={() => {
                    setSelectedRepo(repo);
                    setCloneMessage("");
                  }}
                >
                  <div className="repo-icon">
                    <FolderGit2 size={22} />
                  </div>

                  <div className="repo-details">
                    <h3>{repo.full_name || repo.name}</h3>

                    <p>
                      {repo.description || "No description provided."}
                    </p>

                    <div className="repo-meta">
                      {repo.private ? (
                        <span><Lock size={13} /> Private</span>
                      ) : (
                        <span><Globe size={13} /> Public</span>
                      )}

                      {repo.language && (
                        <span><Code2 size={13} /> {repo.language}</span>
                      )}

                      {repo.default_branch && (
                        <span>
                          <GitBranch size={13} />
                          {repo.default_branch}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="repo-select">
                    {selectedRepo?.id === repo.id ? (
                      <CheckCircle2 size={22} />
                    ) : (
                      <span className="select-circle" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="clone-footer">
            <div className="selected-label">
              {selectedRepo
                ? `Selected: ${selectedRepo.full_name || selectedRepo.name}`
                : "Select a repository to continue"}
            </div>

            <button
              className="clone-button"
              disabled={!selectedRepo || cloning || loading}
              onClick={handleClone}
            >
              {cloning ? (
                <>
                  <RefreshCw className="spin" size={17} />
                  Cloning...
                </>
              ) : (
                <>
                  <Download size={17} />
                  Clone Repository
                </>
              )}
            </button>
          </div>
        </div>

        <div className="security-note">
          <ShieldCheck size={18} />
          Your GitHub credentials are handled by the backend.
          Repository access is limited by your GitHub App installation.
        </div>
      </main>
    </div>
  );
}

function App() {
  const isDashboard = window.location.pathname === "/dashboard";

  return isDashboard ? <Dashboard /> : <LandingPage />;
}

export default App;

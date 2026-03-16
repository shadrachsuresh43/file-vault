import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch, clearToken } from "../api";

type VaultFile = {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};

export default function DashboardPage() {
  const navigate = useNavigate();

  const [files, setFiles] = useState<VaultFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  async function loadFiles() {
    setLoadingFiles(true);
    setErrorMsg("");

    try {
      const response = await apiFetch("/files");

      if (response.status === 401) {
        clearToken();
        navigate("/login");
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Failed to load files");
      }

      const data = await response.json();
      setFiles(data);
    } catch (err) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to load files");
      }
    } finally {
      setLoadingFiles(false);
    }
  }

  useEffect(() => {
    loadFiles();
  }, []);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (!selectedFile) {
      setErrorMsg("Please choose a file first.");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("uploaded_file", selectedFile);

      const response = await apiFetch("/files/upload", {
        method: "POST",
        body: formData,
      });

      if (response.status === 401) {
        clearToken();
        navigate("/login");
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Upload failed");
      }

      setSelectedFile(null);
      setSuccessMsg("File uploaded successfully.");
      await loadFiles();
    } catch (err) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Upload failed");
      }
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(fileId: number, filename: string) {
    try {
      const response = await apiFetch(`/files/${fileId}/download`);

      if (response.status === 401) {
        clearToken();
        navigate("/login");
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Download failed");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Download failed");
      }
    }
  }

  function handleLogout() {
    clearToken();
    navigate("/login");
  }

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <h1>File Vault Dashboard</h1>
        <button onClick={handleLogout}>Logout</button>
      </header>

      <section className="card">
        <h2>Upload File</h2>
        <form onSubmit={handleUpload} className="upload-form">
          <input
            type="file"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
          />
          <button type="submit" disabled={uploading}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Your Files</h2>

        {errorMsg && <p className="error">{errorMsg}</p>}
        {successMsg && <p className="success">{successMsg}</p>}

        {loadingFiles ? (
          <p>Loading files...</p>
        ) : files.length === 0 ? (
          <p>No files uploaded yet.</p>
        ) : (
          <table className="file-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Size (bytes)</th>
                <th>Uploaded</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.id}>
                  <td>{file.original_filename}</td>
                  <td>{file.content_type}</td>
                  <td>{file.size_bytes}</td>
                  <td>{new Date(file.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      onClick={() =>
                        handleDownload(file.id, file.original_filename)
                      }
                    >
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
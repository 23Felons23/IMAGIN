<script>
  import { onDestroy } from 'svelte';
  
  let isDragOver = false;
  let mode = "multimodal";
  let topic = "";
  
  let jobs = [];
  let pollIntervals = {};

  const API_BASE = "http://127.0.0.1:8000";

  function handleDragOver(e) {
    e.preventDefault();
    isDragOver = true;
  }

  function handleDragLeave() {
    isDragOver = false;
  }

  async function handleDrop(e) {
    e.preventDefault();
    isDragOver = false;
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      
      for (const file of files) {
        const localId = Date.now() + Math.random();
        const newJob = {
          id: localId,
          filename: file.name,
          status: 'uploading',
          progress: 5,
          clips: [],
          error: null
        };
        
        jobs = [...jobs, newJob];
        
        const formData = new FormData();
        formData.append("file", file);
        
        try {
          const res = await fetch(`${API_BASE}/api/upload?mode=${mode}&topic=${encodeURIComponent(topic)}`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          
          if (data.job_id) {
            updateJob(localId, { 
              id: data.job_id, 
              status: data.status,
              progress: getProgressFromStatus(data.status)
            });
            startPolling(data.job_id);
          } else {
            updateJob(localId, { status: 'error', error: data.error || 'Upload failed' });
          }
        } catch (err) {
          updateJob(localId, { status: 'error', error: err.message });
        }
      }
    }
  }

  function updateJob(jobId, updates) {
    jobs = jobs.map(j => j.id === jobId ? { ...j, ...updates } : j);
  }

  function getProgressFromStatus(status) {
    switch (status) {
      case 'uploading': return 5;
      case 'processing': return 10;
      case 'extracting_audio': return 25;
      case 'transcribing': return 50;
      case 'extracting_highlights': return 75;
      case 'rendering': return 90;
      case 'complete': return 100;
      case 'error': return 100;
      default: return 0;
    }
  }

  function formatStatus(status) {
    if (!status) return 'Unknown';
    return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  function startPolling(jobId) {
    if (pollIntervals[jobId]) return;
    
    pollIntervals[jobId] = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
        const data = await res.json();
        
        if (data.error) {
          clearInterval(pollIntervals[jobId]);
          updateJob(jobId, { status: 'error', error: data.error });
          return;
        }

        updateJob(jobId, { 
          status: data.status, 
          progress: getProgressFromStatus(data.status),
          clips: data.clips || [],
          error: data.error
        });

        if (data.status === 'complete' || data.status === 'error') {
          clearInterval(pollIntervals[jobId]);
          delete pollIntervals[jobId];
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 2000);
  }

  onDestroy(() => {
    Object.values(pollIntervals).forEach(clearInterval);
  });
</script>

<main>
  <h1>Podcast Pipeline</h1>

  <section 
    class="dropzone {isDragOver ? 'dragover' : ''}" 
    on:dragover={handleDragOver}
    on:dragleave={handleDragLeave}
    on:drop={handleDrop}
  >
    <p>{isDragOver ? "DROP IT NOW!" : "DRAG & DROP MULTICAM VIDEO FILES HERE"}</p>
  </section>

  <section class="config-section">
    <div class="config-title">Highlight Extraction Mode</div>
    <div class="radio-group">
      <label class="radio-label">
        <input type="radio" bind:group={mode} value="multimodal"> Multimodal
      </label>
      <label class="radio-label">
        <input type="radio" bind:group={mode} value="topic"> Topic-Driven
      </label>
    </div>

    {#if mode === 'topic'}
      <input 
        type="text" 
        class="topic-input" 
        bind:value={topic} 
        placeholder="ENTER TOPIC PROMPT (e.g. Find moments about artificial intelligence)" 
      />
    {/if}
  </section>

  {#if jobs.length > 0}
    <section class="jobs-section">
      <h2>Processing Queue</h2>
      {#each jobs as job (job.id)}
        <div class="job-card">
          <div class="job-header">
            <span class="filename">{job.filename}</span>
            <span class="status" style={job.status === 'error' ? 'color: #ff3366;' : ''}>
              {job.error ? `Error: ${job.error}` : formatStatus(job.status)}
            </span>
          </div>
          
          <div class="progress-track">
            <div class="progress-bar" style="width: {job.progress}%; {job.status === 'error' ? 'background-color: #ff3366;' : ''}"></div>
          </div>
          
          {#if job.status === 'complete' && job.clips && job.clips.length > 0}
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px;">
              {#each job.clips as clipPath, index}
                {@const filename = clipPath.split(/[/\\]/).pop()}
                <a class="btn-download" style="text-decoration: none; display: inline-block; padding: 10px 20px;" href="{API_BASE}/api/jobs/{job.id}/download/{filename}" target="_blank" download>
                  Download Clip {index + 1}
                </a>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </section>
  {/if}
</main>

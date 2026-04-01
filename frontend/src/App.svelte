<script>
  let isDragOver = false;
  let mode = "multimodal";
  let topic = "";
  
  let jobs = [];

  function handleDragOver(e) {
    e.preventDefault();
    isDragOver = true;
  }

  function handleDragLeave() {
    isDragOver = false;
  }

  function handleDrop(e) {
    e.preventDefault();
    isDragOver = false;
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      
      files.forEach(file => {
        const newJob = {
          id: Date.now() + Math.random(),
          filename: file.name,
          status: 'Processing...',
          progress: 0
        };
        
        jobs = [...jobs, newJob];
        simulateProcessing(newJob.id);
      });
    }
  }

  function simulateProcessing(jobId) {
    const interval = setInterval(() => {
      jobs = jobs.map(job => {
        if (job.id === jobId) {
          const newProgress = job.progress + 10;
          if (newProgress >= 100) {
            clearInterval(interval);
            return { ...job, progress: 100, status: 'Complete' };
          }
          return { ...job, progress: newProgress };
        }
        return job;
      });
    }, 500);
  }

  function downloadVideo(job) {
    alert(`Video Ready! Downloading edited output for ${job.filename}...`);
  }
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
        placeholder="ENTER TOPIC PROMPT (e.g. Find moments about Artificial Intelligence)" 
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
            <span class="status">{job.status}</span>
          </div>
          
          <div class="progress-track">
            <div class="progress-bar" style="width: {job.progress}%"></div>
          </div>
          
          {#if job.status === 'Complete'}
            <button class="btn-download" on:click={() => downloadVideo(job)}>
              Download MP4
            </button>
          {/if}
        </div>
      {/each}
    </section>
  {/if}
</main>

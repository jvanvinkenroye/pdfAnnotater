// Shared helper for polling background jobs (OCR, PDF export).
//
// pollJob(jobId) resolves with the job's status JSON once the job is
// "done", and rejects with an Error when the job reports "error", the
// status request fails, or the client-side timeout is reached (safety
// net in case the server lost the job, e.g. across a restart).
function pollJob(jobId, options) {
    const intervalMs = (options && options.intervalMs) || 2000;
    const timeoutMs = (options && options.timeoutMs) || 15 * 60 * 1000;
    const deadline = Date.now() + timeoutMs;

    return new Promise((resolve, reject) => {
        function check() {
            fetch(`/viewer/api/jobs/${jobId}`)
                .then(response => {
                    if (!response.ok) {
                        return response.json().catch(() => ({})).then(data => {
                            throw new Error(data.error || 'Statusabfrage fehlgeschlagen');
                        });
                    }
                    return response.json();
                })
                .then(job => {
                    if (job.status === 'done') {
                        resolve(job);
                    } else if (job.status === 'error') {
                        reject(new Error(job.error || 'Vorgang fehlgeschlagen'));
                    } else if (Date.now() > deadline) {
                        reject(new Error('Zeitüberschreitung – bitte später erneut versuchen'));
                    } else {
                        setTimeout(check, intervalMs);
                    }
                })
                .catch(reject);
        }
        check();
    });
}

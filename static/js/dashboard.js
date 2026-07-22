(() => {
    const root = document.getElementById('dashboard');
    if (!root) return;

    const connected = {
        facebook: root.dataset.facebookConnected === 'true',
        tiktok: root.dataset.tiktokConnected === 'true',
    };
    const compactNumber = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
    const fullNumber = new Intl.NumberFormat('en');
    let viewsChart;
    let engagementChart;

    const fetchPlatform = async (platform) => {
        if (!connected[platform]) return null;
        const response = await fetch(`/api/v1/stats/${platform}`, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        });
        const payload = await response.json().catch(() => ({ error: 'Invalid server response' }));
        if (!response.ok) throw new Error(`${platform}: ${payload.error || 'Request failed'}`);
        return payload;
    };

    const loadDashboard = async () => {
        const platforms = Object.keys(connected).filter((key) => connected[key]);
        if (!platforms.length) {
            renderEmptyState();
            return;
        }
        const results = await Promise.allSettled(platforms.map(fetchPlatform));
        const data = results.filter((item) => item.status === 'fulfilled' && item.value).map((item) => item.value);
        const errors = results.filter((item) => item.status === 'rejected').map((item) => item.reason.message);
        if (errors.length) showNotice(errors.join(' | '));
        if (!data.length) {
            renderEmptyState('Connected channels could not return performance data.');
            return;
        }
        renderMetrics(data);
        renderCharts(data);
        renderTable(data);
        document.getElementById('lastUpdated').textContent = `Updated ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    };

    const renderMetrics = (datasets) => {
        const totals = datasets.reduce((acc, item) => {
            acc.views += item.summary.views || 0;
            acc.engagement += item.summary.engagement || 0;
            acc.content += item.summary.content_count || 0;
            return acc;
        }, { views: 0, engagement: 0, content: 0 });
        document.getElementById('totalViews').textContent = compactNumber.format(totals.views);
        document.getElementById('totalEngagement').textContent = compactNumber.format(totals.engagement);
        document.getElementById('contentCount').textContent = fullNumber.format(totals.content);
        const rate = totals.views ? (totals.engagement / totals.views) * 100 : 0;
        document.getElementById('engagementRate').textContent = `${rate.toFixed(rate >= 10 ? 1 : 2)}%`;
    };

    const renderCharts = (datasets) => {
        const allDates = [...new Set(datasets.flatMap((item) => item.daily.map((day) => day.date)))].sort();
        const colors = { facebook: '#2563eb', tiktok: '#18181b' };
        const dailySets = datasets.map((item) => ({
            label: item.platform === 'facebook' ? 'Facebook' : 'TikTok',
            data: allDates.map((date) => item.daily.find((day) => day.date === date)?.views || 0),
            borderColor: colors[item.platform],
            backgroundColor: `${colors[item.platform]}18`,
            pointRadius: 2,
            pointHoverRadius: 5,
            borderWidth: 2,
            tension: 0.35,
            fill: false,
        }));
        viewsChart?.destroy();
        viewsChart = new Chart(document.getElementById('viewsChart'), {
            type: 'line',
            data: { labels: allDates.map(formatDate), datasets: dailySets },
            options: chartOptions('Views'),
        });

        const topContent = datasets.flatMap((item) => item.content.map((content) => ({ ...content, platform: item.platform })))
            .sort((a, b) => b.engagement - a.engagement).slice(0, 8).reverse();
        engagementChart?.destroy();
        engagementChart = new Chart(document.getElementById('engagementChart'), {
            type: 'bar',
            data: {
                labels: topContent.map((item) => truncate(item.title, 22)),
                datasets: [{
                    label: 'Engagement',
                    data: topContent.map((item) => item.engagement),
                    backgroundColor: topContent.map((item) => colors[item.platform]),
                    borderRadius: 3,
                    barThickness: 14,
                }],
            },
            options: { ...chartOptions('Engagement'), indexAxis: 'y' },
        });
    };

    const chartOptions = (label) => ({
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 7, boxHeight: 7, font: { family: 'DM Sans', size: 11 } } },
            tooltip: { callbacks: { label: (context) => `${context.dataset.label || label}: ${fullNumber.format(context.parsed.y ?? context.parsed.x)}` } },
        },
        scales: {
            x: { grid: { display: false }, ticks: { color: '#71717a', font: { family: 'DM Sans', size: 10 }, maxRotation: 0, autoSkip: true } },
            y: { beginAtZero: true, border: { display: false }, grid: { color: '#f4f4f5' }, ticks: { color: '#71717a', callback: (value) => compactNumber.format(value), font: { family: 'DM Sans', size: 10 } } },
        },
    });

    const renderTable = (datasets) => {
        const rows = datasets.flatMap((item) => item.content.map((content) => ({ ...content, platform: item.platform })))
            .sort((a, b) => b.engagement - a.engagement).slice(0, 10);
        const table = document.getElementById('contentTable');
        if (!rows.length) {
            table.innerHTML = '<tr><td colspan="5" class="px-5 py-10 text-center text-zinc-500">No published content was returned.</td></tr>';
            return;
        }
        table.replaceChildren(...rows.map((item) => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-zinc-50';
            const titleCell = document.createElement('td');
            titleCell.className = 'max-w-sm px-5 py-3.5 font-medium text-zinc-800';
            if (item.url) {
                const link = document.createElement('a');
                link.href = item.url;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.className = 'hover:underline';
                link.textContent = item.title;
                titleCell.appendChild(link);
            } else titleCell.textContent = item.title;
            row.append(titleCell, tableCell(titleCase(item.platform), 'px-5 py-3.5 text-zinc-500'), tableCell(fullNumber.format(item.views), 'px-5 py-3.5 text-right tabular-nums'), tableCell(fullNumber.format(item.engagement), 'px-5 py-3.5 text-right tabular-nums font-semibold'), tableCell(item.average_watch_time ? `${item.average_watch_time.toFixed(1)}s` : '--', 'px-5 py-3.5 text-right tabular-nums text-zinc-500'));
            return row;
        }));
    };

    const tableCell = (text, className) => {
        const cell = document.createElement('td');
        cell.className = className;
        cell.textContent = text;
        return cell;
    };
    const renderEmptyState = (message = 'Connect Facebook or TikTok to load performance data.') => {
        ['totalViews', 'totalEngagement', 'contentCount', 'engagementRate'].forEach((id) => { document.getElementById(id).textContent = '0'; });
        document.getElementById('contentTable').innerHTML = `<tr><td colspan="5" class="px-5 py-10 text-center text-zinc-500">${message}</td></tr>`;
        showNotice(message);
        renderCharts([]);
    };
    const showNotice = (message) => { const notice = document.getElementById('dataNotice'); notice.textContent = message; notice.classList.remove('hidden'); };
    const truncate = (value, length) => value.length > length ? `${value.slice(0, length - 1)}…` : value;
    const titleCase = (value) => value.charAt(0).toUpperCase() + value.slice(1);
    const formatDate = (value) => new Date(`${value}T00:00:00`).toLocaleDateString([], { month: 'short', day: 'numeric' });

    loadDashboard().catch((error) => { showNotice(error.message); renderEmptyState('Unable to load dashboard data.'); });
})();

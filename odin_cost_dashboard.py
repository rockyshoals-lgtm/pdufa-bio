"""
ODIN Cost Control Dashboard
Real-time web UI for monitoring and controlling spending
Run: python odin_cost_dashboard.py
Visit: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify, request
from odin_cost_control import OdinCostController
import json
import asyncio
from datetime import datetime

app = Flask(__name__)
controller = OdinCostController()

# HTML Template for dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ODIN Cost Control Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e0e7ff;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #312e81;
            padding-bottom: 20px;
        }
        
        h1 {
            font-size: 28px;
            color: #a78bfa;
            margin-bottom: 10px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            background: #312e81;
            color: #a78bfa;
        }
        
        .status-badge.ok { background: #10b981; color: white; }
        .status-badge.warning { background: #f59e0b; color: white; }
        .status-badge.danger { background: #ef4444; color: white; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: #1e293b;
            border: 1px solid #312e81;
            border-radius: 8px;
            padding: 20px;
        }
        
        .card h2 {
            font-size: 14px;
            color: #94a3b8;
            text-transform: uppercase;
            margin-bottom: 12px;
            font-weight: 600;
            letter-spacing: 1px;
        }
        
        .card-value {
            font-size: 32px;
            font-weight: bold;
            color: #a78bfa;
            margin-bottom: 8px;
        }
        
        .card-subtext {
            font-size: 12px;
            color: #64748b;
        }
        
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #312e81;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 12px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981, #a78bfa);
            transition: width 0.3s ease;
        }
        
        .progress-fill.warning { background: linear-gradient(90deg, #f59e0b, #ef4444); }
        
        .ai-breakdown {
            margin-top: 30px;
        }
        
        .ai-breakdown h2 {
            font-size: 18px;
            color: #a78bfa;
            margin-bottom: 20px;
        }
        
        .ai-row {
            display: grid;
            grid-template-columns: 150px 1fr 100px 100px;
            gap: 20px;
            padding: 15px;
            background: #0f172a;
            border-bottom: 1px solid #312e81;
            align-items: center;
        }
        
        .ai-name {
            font-weight: 600;
            color: #a78bfa;
        }
        
        .ai-bar {
            height: 4px;
            background: #312e81;
            border-radius: 2px;
            overflow: hidden;
        }
        
        .ai-bar-fill {
            height: 100%;
            background: #06b6d4;
            transition: width 0.3s ease;
        }
        
        .ai-cost {
            text-align: right;
            font-weight: 600;
        }
        
        .ai-limit {
            text-align: right;
            font-size: 12px;
            color: #64748b;
        }
        
        .controls {
            margin-top: 30px;
            padding: 20px;
            background: #1e293b;
            border: 1px solid #312e81;
            border-radius: 8px;
        }
        
        .controls h2 {
            font-size: 18px;
            color: #a78bfa;
            margin-bottom: 20px;
        }
        
        .control-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 10px 20px;
            border: 1px solid #312e81;
            background: #312e81;
            color: #a78bfa;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        button:hover {
            background: #4c1d95;
            border-color: #a78bfa;
        }
        
        button.active {
            background: #a78bfa;
            color: #0f172a;
        }
        
        input {
            padding: 10px 15px;
            background: #0f172a;
            border: 1px solid #312e81;
            border-radius: 6px;
            color: #e0e7ff;
            font-size: 14px;
        }
        
        input:focus {
            outline: none;
            border-color: #a78bfa;
        }
        
        .alert {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        
        .alert.info {
            background: #312e81;
            color: #a78bfa;
            border-left: 4px solid #a78bfa;
        }
        
        .alert.warning {
            background: #78350f;
            color: #fcd34d;
            border-left: 4px solid #fcd34d;
        }
        
        .alert.danger {
            background: #7f1d1d;
            color: #fca5a5;
            border-left: 4px solid #fca5a5;
        }
        
        .timestamp {
            text-align: center;
            color: #64748b;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 ODIN Cost Control Dashboard</h1>
            <div class="status-badge ok" id="status">Connected</div>
            <p id="current-level" style="margin-top: 10px; color: #94a3b8;"></p>
        </header>
        
        <div class="grid" id="summary-cards">
            <!-- Cards will be filled by JavaScript -->
        </div>
        
        <div class="ai-breakdown">
            <h2>Per-AI Spending Breakdown</h2>
            <div id="ai-breakdown">
                <!-- AI breakdown will be filled by JavaScript -->
            </div>
        </div>
        
        <div class="controls">
            <h2>💰 Budget Controls</h2>
            
            <div class="alert info">
                <strong>Spending Level:</strong> <span id="level-display">moderate</span>
            </div>
            
            <h3 style="color: #94a3b8; margin-bottom: 15px; font-size: 14px;">Quick Presets:</h3>
            <div class="control-group">
                <button id="btn-minimal">Minimal ($15/day)</button>
                <button id="btn-conservative">Conservative ($50/day)</button>
                <button id="btn-moderate" class="active">Moderate ($145/day)</button>
                <button id="btn-aggressive">Aggressive ($465/day)</button>
            </div>
            
            <h3 style="color: #94a3b8; margin-bottom: 15px; font-size: 14px; margin-top: 25px;">Or Set Custom Limits:</h3>
            <div class="control-group">
                <div style="flex: 1; min-width: 150px;">
                    <label style="display: block; font-size: 12px; color: #64748b; margin-bottom: 5px;">Daily Limit ($)</label>
                    <input type="number" id="custom-daily" placeholder="145" style="width: 100%;">
                </div>
                <div style="flex: 1; min-width: 150px;">
                    <label style="display: block; font-size: 12px; color: #64748b; margin-bottom: 5px;">Weekly Limit ($)</label>
                    <input type="number" id="custom-weekly" placeholder="1015" style="width: 100%;">
                </div>
                <div style="flex: 1; min-width: 150px;">
                    <label style="display: block; font-size: 12px; color: #64748b; margin-bottom: 5px;">Monthly Limit ($)</label>
                    <input type="number" id="custom-monthly" placeholder="4350" style="width: 100%;">
                </div>
                <button id="btn-custom" style="align-self: flex-end; margin-bottom: 0;">Apply Custom</button>
            </div>
            
            <h3 style="color: #94a3b8; margin-bottom: 15px; font-size: 14px; margin-top: 25px;">Settings:</h3>
            <div class="control-group">
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                    <input type="checkbox" id="auto-throttle" checked style="width: auto;">
                    <span>Auto-Throttle (block calls when over budget)</span>
                </label>
            </div>
        </div>
        
        <div class="timestamp" id="last-update">
            Last updated: --:--:--
        </div>
    </div>
    
    <script>
        // Fetch and display data
        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // Update summary cards
                const summaryHtml = `
                    <div class="card">
                        <h2>Today</h2>
                        <div class="card-value">$${data.daily.total_cost.toFixed(2)}</div>
                        <div class="card-subtext">of $${data.daily.daily_budget.toFixed(2)}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${data.daily.percent_used}%"></div>
                        </div>
                        <div style="margin-top: 8px; font-size: 11px; color: #64748b;">
                            ${data.daily.percent_used.toFixed(1)}% used · $${data.daily.remaining.toFixed(2)} remaining
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>This Week</h2>
                        <div class="card-value">$${data.weekly.total_cost.toFixed(2)}</div>
                        <div class="card-subtext">of $${data.weekly.weekly_budget.toFixed(2)}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${data.weekly.percent_used}%"></div>
                        </div>
                        <div style="margin-top: 8px; font-size: 11px; color: #64748b;">
                            ${data.weekly.percent_used.toFixed(1)}% used · $${data.weekly.remaining.toFixed(2)} remaining
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>This Month</h2>
                        <div class="card-value">$${data.monthly.total_cost.toFixed(2)}</div>
                        <div class="card-subtext">of $${data.monthly.monthly_budget.toFixed(2)}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${data.monthly.percent_used}%"></div>
                        </div>
                        <div style="margin-top: 8px; font-size: 11px; color: #64748b;">
                            ${data.monthly.percent_used.toFixed(1)}% used · $${data.monthly.remaining.toFixed(2)} remaining
                        </div>
                    </div>
                `;
                document.getElementById('summary-cards').innerHTML = summaryHtml;
                
                // Update AI breakdown
                let aiHtml = '';
                for (const [ai, info] of Object.entries(data.daily.by_ai)) {
                    const pct = (info.cost / info.daily_limit * 100).toFixed(1);
                    aiHtml += `
                        <div class="ai-row">
                            <div class="ai-name">${ai.toUpperCase()}</div>
                            <div class="ai-bar">
                                <div class="ai-bar-fill" style="width: ${Math.min(pct, 100)}%"></div>
                            </div>
                            <div class="ai-cost">$${info.cost.toFixed(2)}</div>
                            <div class="ai-limit">/$${info.daily_limit.toFixed(2)}</div>
                        </div>
                    `;
                }
                document.getElementById('ai-breakdown').innerHTML = aiHtml;
                
                // Update level display
                document.getElementById('level-display').textContent = data.spending_level;
                document.getElementById('current-level').textContent = `Current Budget: ${data.spending_level.toUpperCase()}`;
                
                // Update timestamp
                const now = new Date();
                document.getElementById('last-update').textContent = `Last updated: ${now.toLocaleTimeString()}`;
                
            } catch (error) {
                console.error('Error fetching dashboard data:', error);
            }
        }
        
        // Button handlers
        document.getElementById('btn-minimal').onclick = () => changeBudget('minimal');
        document.getElementById('btn-conservative').onclick = () => changeBudget('conservative');
        document.getElementById('btn-moderate').onclick = () => changeBudget('moderate');
        document.getElementById('btn-aggressive').onclick = () => changeBudget('aggressive');
        document.getElementById('btn-custom').onclick = applyCustomBudget;
        
        async function changeBudget(level) {
            try {
                const response = await fetch('/api/set-level', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ level })
                });
                const data = await response.json();
                updateDashboard();
                
                // Update active button
                document.querySelectorAll('.control-group button').forEach(b => b.classList.remove('active'));
                event.target.classList.add('active');
            } catch (error) {
                console.error('Error changing budget:', error);
            }
        }
        
        async function applyCustomBudget() {
            const daily = parseFloat(document.getElementById('custom-daily').value);
            const weekly = parseFloat(document.getElementById('custom-weekly').value);
            const monthly = parseFloat(document.getElementById('custom-monthly').value);
            
            try {
                const response = await fetch('/api/set-custom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ daily, weekly, monthly })
                });
                const data = await response.json();
                updateDashboard();
            } catch (error) {
                console.error('Error setting custom budget:', error);
            }
        }
        
        // Initial load and refresh every 5 seconds
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    daily = controller.get_daily_summary()
    weekly = controller.get_weekly_summary()
    monthly = controller.get_monthly_summary()
    
    return jsonify({
        'spending_level': controller.config['spending_level'],
        'daily': daily,
        'weekly': weekly,
        'monthly': monthly
    })

@app.route('/api/set-level', methods=['POST'])
def api_set_level():
    data = request.json
    controller.set_spending_level(data['level'])
    return jsonify({'success': True})

@app.route('/api/set-custom', methods=['POST'])
def api_set_custom():
    data = request.json
    controller.set_custom_budget(
        daily=data.get('daily'),
        weekly=data.get('weekly'),
        monthly=data.get('monthly')
    )
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n🚀 ODIN Cost Dashboard starting...")
    print("📊 Open your browser: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop\n")
    app.run(debug=True, host='localhost', port=5000)

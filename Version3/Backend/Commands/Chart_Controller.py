import os
import json
import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import System_Configuration as System_Configuration

def generate_chart(chart_type: str, title: str, labels_json: str, values_json: str):
    try:
        output_dir = System_Configuration.TEMPORARY_FOLDER_PATH
        os.makedirs(output_dir, exist_ok=True)

        labels = json.loads(labels_json)
        values = json.loads(values_json)
        
        # Enable Dark HUD Theme for Matplotlib
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6, 3.8), dpi=120)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        # Neon Cyan accents
        bar_color = '#38bdf8'
        edge_color = '#0284c7'
        text_color = '#f8fafc'
        grid_color = (56 / 255, 189 / 255, 248 / 255, 0.15)

        if chart_type.lower() == "bar":
            bars = ax.bar(labels, values, color=bar_color, edgecolor=edge_color, linewidth=1.5, width=0.5)
            ax.grid(axis='y', linestyle='--', alpha=0.3, color='#38bdf8')
        elif chart_type.lower() == "line":
            ax.plot(labels, values, marker="o", color=bar_color, linewidth=2.5, markersize=6, markerfacecolor='#e0f2fe')
            ax.grid(True, linestyle='--', alpha=0.3, color='#38bdf8')
        elif chart_type.lower() == "pie":
            colors = ['#38bdf8', '#0284c7', '#0369a1', '#0c4a6e', '#7dd3fc']
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140, colors=colors[:len(values)], textprops={'color': text_color})
        else:
            return f"Unsupported chart type: {chart_type}. Use 'bar', 'line', or 'pie'."
            
        ax.set_title(title, color=bar_color, fontsize=12, fontweight='bold', pad=12)
        ax.tick_params(colors=text_color, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')
            
        plt.tight_layout()

        # Create a unique filename using a timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = os.path.join(output_dir, f"chart_{timestamp}.png")
        latest_filename = os.path.join(output_dir, "latest_chart.png")
        
        plt.savefig(unique_filename, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
        plt.savefig(latest_filename, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
        plt.close()
        
        return f"[CHART_IMG:{os.path.basename(unique_filename)}] Chart '{title}' generated successfully!"
    except Exception as e:
        return f"Error generating chart: {str(e)}"
from flask import Flask, render_template, jsonify, request, redirect, url_for
from dotenv import load_dotenv
import os
import json
import pandas as pd
import math

# Load environment variables
load_dotenv()

# Create Flask application
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'


def create_keeper_analysis_dataframe():
    """
    Create a comprehensive dataframe for keeper analysis combining draft results and fantasy pros data.
    """
    try:
        # Load draft results
        with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'draft_results.json'), 'r') as f:
            draft_data = json.load(f)

        # Load fantasy pros data
        fantasy_pros_df = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', 'data', 'fantasy_pros.csv'))

        # Create team name to manager mapping
        team_to_manager = {}
        for team in draft_data['teams']:
            team_to_manager[team['team_name']] = team['manager']

        # Create draft results DataFrame
        draft_records = []
        for pick in draft_data['draft_picks']:
            manager_name = team_to_manager.get(pick['drafting_team'], pick['drafting_team'])
            draft_records.append({
                'player_name': pick['player_name'],
                '2024_manager': manager_name,
                '2024_draft_round': pick.get('round'),
                '2024_overall_pick': pick.get('overall_pick'),
                '2024_keeper_status': pick['keeper_status'],
                '2025_keeper_eligible': pick.get('2025_keeper_eligible', True),
                'waiver_pickup': pick.get('waiver_pickup', False)
            })

        draft_df = pd.DataFrame(draft_records)

        # Clean up fantasy pros data
        fantasy_pros_df = fantasy_pros_df.rename(columns={
            'PLAYER NAME': 'player_name',
            'RK': '2025_draft_rank',
            'POS': '2025_position_rank'
        })

        # Clean player names for better matching
        draft_df['player_name_clean'] = draft_df['player_name'].str.strip()
        fantasy_pros_df['player_name_clean'] = fantasy_pros_df['player_name'].str.strip()

        # Merge the dataframes
        merged_df = pd.merge(
            draft_df,
            fantasy_pros_df[['player_name_clean', '2025_draft_rank', '2025_position_rank']],
            on='player_name_clean',
            how='left'
        )

        # Calculate derived columns
        # 2025 projected draft round (rank divided by 12, rounded up)
        merged_df['2025_projected_draft_round'] = merged_df['2025_draft_rank'].apply(
            lambda x: math.ceil(x / 12) if pd.notna(x) else None
        )

        # 2025 keeper round (2024 round - 1, minimum of 1, or round 5 for waiver pickups)
        def calculate_keeper_round_local(row):
            if row['waiver_pickup']:
                return 5  # Waiver pickups get keeper round 5
            elif pd.notna(row['2024_draft_round']):
                return max(1, row['2024_draft_round'] - 1)  # Drafted players: round - 1, minimum 1
            else:
                return None  # No draft round and not waiver pickup

        merged_df['2025_keeper_round'] = merged_df.apply(calculate_keeper_round_local, axis=1)

        # Select and order the final columns
        final_columns = [
            'player_name',
            '2024_manager',
            '2024_draft_round',
            '2024_overall_pick',
            '2024_keeper_status',
            '2025_keeper_eligible',
            '2025_draft_rank',
            '2025_position_rank',
            '2025_projected_draft_round',
            '2025_keeper_round',
            'waiver_pickup'
        ]

        result_df = merged_df[final_columns].copy()

        # Filter out kickers and defenses
        result_df = result_df[
            ~result_df['2025_position_rank'].astype(str).str.startswith(('K', 'DST'), na=False)
        ].copy()

        # Filter out players with no 2025 rank (not found in fantasy_pros.csv)
        result_df = result_df[result_df['2025_draft_rank'].notna()].copy()

        # Sort by 2024 overall pick
        result_df = result_df.sort_values('2024_overall_pick').reset_index(drop=True)

        return result_df

    except Exception as e:
        print(f"Error creating keeper analysis dataframe: {e}")
        return pd.DataFrame()


@app.route('/')
def index():
    """Home page redirects to keeper analysis."""
    return redirect(url_for('keeper_analysis'))


@app.route('/keeper-analysis')
def keeper_analysis():
    """Main keeper analysis page."""
    try:
        # Get the keeper analysis data
        df = create_keeper_analysis_dataframe()

        if df.empty:
            return render_template('error.html',
                                   error_message="Unable to load keeper analysis data")

        # Convert to list of dictionaries for template
        players = df.to_dict('records')

        # Get unique managers for filter
        managers = sorted(df['2024_manager'].dropna().unique().tolist())

        return render_template('keeper_analysis.html',
                               players=players,
                               managers=managers)

    except Exception as e:
        print(f"Error in keeper_analysis route: {e}")
        return render_template('error.html',
                               error_message="An error occurred while loading the keeper analysis")


@app.route('/api/players')
def api_players():
    """API endpoint to get all players data."""
    try:
        df = create_keeper_analysis_dataframe()

        if df.empty:
            return jsonify({
                'error': 'No data available',
                'status': 'error'
            }), 404

        # Convert to list of dictionaries
        players = df.to_dict('records')

        return jsonify({
            'players': players,
            'total_count': len(players),
            'status': 'success'
        })

    except Exception as e:
        print(f"Error in api_players: {e}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500


@app.route('/api/managers')
def api_managers():
    """API endpoint to get all managers."""
    try:
        df = create_keeper_analysis_dataframe()

        if df.empty:
            return jsonify({
                'error': 'No data available',
                'status': 'error'
            }), 404

        managers = sorted(df['2024_manager'].dropna().unique().tolist())

        return jsonify({
            'managers': managers,
            'status': 'success'
        })

    except Exception as e:
        print(f"Error in api_managers: {e}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500


@app.route('/api/keeper-recommendations/<manager>')
def api_keeper_recommendations(manager):
    """API endpoint to get keeper recommendations for a specific manager."""
    try:
        df = create_keeper_analysis_dataframe()

        if df.empty:
            return jsonify({
                'error': 'No data available',
                'status': 'error'
            }), 404

        # Filter for the specific manager and eligible keepers
        manager_df = df[
            (df['2024_manager'] == manager) &
            (df['2025_keeper_eligible'] == True)
        ].copy()

        if manager_df.empty:
            return jsonify({
                'manager': manager,
                'recommendations': [],
                'message': 'No eligible keepers found for this manager',
                'status': 'success'
            })

        # Calculate value (projected round - keeper round)
        manager_df['keeper_value'] = manager_df['2025_projected_draft_round'] - manager_df['2025_keeper_round']

        # Sort by value (highest first) and get top recommendations
        recommendations = manager_df.nlargest(5, 'keeper_value').to_dict('records')

        return jsonify({
            'manager': manager,
            'recommendations': recommendations,
            'status': 'success'
        })

    except Exception as e:
        print(f"Error in api_keeper_recommendations: {e}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html',
                           error_message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html',
                           error_message="Internal server error"), 500


@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error
    print(f"Unhandled exception: {e}")

    # Return JSON error for API routes
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500

    # Return HTML error page for regular routes
    return render_template('error.html',
                           error_message="An unexpected error occurred"), 500


# Export the Flask app for Vercel
# Vercel will automatically detect this as the WSGI application
def application(environ, start_response):
    return app(environ, start_response)


if __name__ == '__main__':
    app.run(
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=int(5001),
        debug=app.config['DEBUG']
    )

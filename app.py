from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import os
import json
import pandas as pd
import math

# Load environment variables
load_dotenv()

# Create Flask application
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'


def create_keeper_analysis_dataframe():
    """
    Create a pandas DataFrame combining draft results with fantasy projections.

    Returns:
        pd.DataFrame: DataFrame with columns for 2024 team, draft round, 2025 projections, etc.
    """
    try:
        # Load draft results JSON
        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        # Load fantasy pros CSV
        fantasy_df = pd.read_csv('data/fantasy_pros.csv')

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
        fantasy_df = fantasy_df.rename(columns={
            'PLAYER NAME': 'player_name',
            'RK': '2025_draft_rank',
            'POS': '2025_position_rank'
        })

        # Clean player names for better matching
        draft_df['player_name_clean'] = draft_df['player_name'].str.strip()
        fantasy_df['player_name_clean'] = fantasy_df['player_name'].str.strip()

        # Merge the dataframes
        merged_df = pd.merge(
            draft_df,
            fantasy_df[['player_name_clean', '2025_draft_rank', '2025_position_rank']],
            on='player_name_clean',
            how='left'
        )

        # Calculate derived columns
        # 2025 projected draft round (rank divided by 12, rounded up)
        merged_df['2025_projected_draft_round'] = merged_df['2025_draft_rank'].apply(
            lambda x: math.ceil(x / 12) if pd.notna(x) else None
        )

        # 2025 keeper round (2024 round - 1, minimum of 1, or round 5 for waiver pickups)
        def calculate_keeper_round(row):
            if row['waiver_pickup']:
                return 5  # Waiver pickups get keeper round 5
            elif pd.notna(row['2024_draft_round']):
                return max(1, row['2024_draft_round'] - 1)  # Drafted players: round - 1, minimum 1
            else:
                return None  # No draft round and not waiver pickup

        merged_df['2025_keeper_round'] = merged_df.apply(calculate_keeper_round, axis=1)

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

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return None
    except Exception as e:
        print(f"❌ Error creating dataframe: {e}")
        return None


@app.cli.command()
def hello():
    """Simple Hello World CLI command."""
    print("Hello World!")


@app.cli.command()
def status():
    """Check the application status."""
    print("LOL Keepers app is ready!")
    print(f"Debug mode: {app.config['DEBUG']}")
    print(f"Secret key configured: {'Yes' if app.config['SECRET_KEY'] else 'No'}")


@app.cli.command()
def draft_summary():
    """Display draft summary information."""
    try:
        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        print("🏈 2024 Fantasy Football Draft Summary")
        print("=" * 40)
        print(f"Total Teams: {draft_data['draft_info']['total_teams']}")
        print(f"Total Rounds: {draft_data['draft_info']['total_rounds']}")
        print(f"Draft Type: {draft_data['draft_info']['draft_type'].title()}")
        print(f"Total Players Drafted: {len(draft_data['draft_picks'])}")
        print("\n📋 Teams & Managers:")
        for team in draft_data['teams']:
            level_emoji = {"Platinum": "🏆", "Gold": "🥇", "Silver": "🥈", "Bronze": "🥉"}.get(team['level'], "")
            print(f"  {team['team_id']:2d}. {team['team_name']} (Manager: {team['manager']}) {level_emoji}")

    except FileNotFoundError:
        print("❌ Draft results file not found. Please ensure data/draft_results.json exists.")
    except json.JSONDecodeError:
        print("❌ Error reading draft results file. Please check the JSON format.")
    except Exception as e:
        print(f"❌ Error loading draft data: {e}")


@app.cli.command()
def team_roster():
    """Show roster for a specific team."""
    try:
        team_name = input("Enter team name (or part of name): ").strip()
        if not team_name:
            print("❌ Team name required.")
            return

        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        # Find matching team
        matching_teams = [team for team in draft_data['teams']
                          if team_name.lower() in team['team_name'].lower()]

        if not matching_teams:
            print(f"❌ No team found matching '{team_name}'")
            return
        elif len(matching_teams) > 1:
            print("Multiple teams found:")
            for team in matching_teams:
                print(f"  - {team['team_name']}")
            return

        selected_team = matching_teams[0]
        team_picks = [pick for pick in draft_data['draft_picks']
                      if pick['team_id'] == selected_team['team_id']]
        team_picks.sort(key=lambda x: x['overall_pick'])

        print(f"\n🏈 {selected_team['team_name']} (Manager: {selected_team['manager']})")
        print(f"Rank: #{selected_team['rank']} | Rating: {selected_team['rating']} | Level: {selected_team['level']}")
        print("=" * 60)
        for pick in team_picks:
            keeper = " (K)" if pick['keeper_status'] else ""
            print(f"Round {pick['round']:2d} (Pick {pick['overall_pick']:3d}): {pick['player_name']}{keeper}")

    except FileNotFoundError:
        print("❌ Draft results file not found.")
    except Exception as e:
        print(f"❌ Error: {e}")


@app.cli.command()
def league_standings():
    """Display league standings with manager ratings and levels."""
    try:
        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        # Sort teams by rank
        teams_by_rank = sorted(draft_data['teams'], key=lambda x: x['rank'])

        print("🏆 League Standings - 2024 Season")
        print("=" * 55)
        print(f"{'Rank':<4} {'Manager':<10} {'Team':<25} {'Rating':<8} {'Level'}")
        print("-" * 55)

        for team in teams_by_rank:
            level_emoji = {"Platinum": "🏆", "Gold": "🥇", "Silver": "🥈", "Bronze": "🥉"}.get(team['level'], "")
            print(
                f"{team['rank']:<4} {team['manager']:<10} {team['team_name'][:24]:<25} {team['rating']:<8} {team['level']} {level_emoji}")

    except FileNotFoundError:
        print("❌ Draft results file not found.")
    except Exception as e:
        print(f"❌ Error: {e}")


@app.cli.command()
def list_keepers():
    """Display all players marked as keepers."""
    try:
        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        keepers = [pick for pick in draft_data['draft_picks'] if pick['keeper_status']]

        if not keepers:
            print("📋 No keepers currently marked in the system.")
            return

        print("🔒 2024 League Keepers")
        print("=" * 50)
        keepers.sort(key=lambda x: x['overall_pick'])

        for keeper in keepers:
            team_info = next(team for team in draft_data['teams'] if team['team_id'] == keeper['team_id'])
            print(f"Round {keeper['round']:2d} (Pick {keeper['overall_pick']:3d}): {keeper['player_name']}")
            print(f"    Team: {keeper['drafting_team']} (Manager: {team_info['manager']})")

    except FileNotFoundError:
        print("❌ Draft results file not found.")
    except Exception as e:
        print(f"❌ Error: {e}")


@app.cli.command()
def update_keeper():
    """Mark a player as keeper or remove keeper status."""
    try:
        player_name = input("Enter player name to update: ").strip()
        if not player_name:
            print("❌ Player name required.")
            return

        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        # Find matching players
        matching_players = [pick for pick in draft_data['draft_picks']
                            if player_name.lower() in pick['player_name'].lower()]

        if not matching_players:
            print(f"❌ No player found matching '{player_name}'")
            return
        elif len(matching_players) > 1:
            print("Multiple players found:")
            for i, player in enumerate(matching_players, 1):
                status = "(K)" if player['keeper_status'] else ""
                print(f"  {i}. {player['player_name']} - {player['drafting_team']} {status}")
            return

        player = matching_players[0]
        current_status = player['keeper_status']
        new_status = not current_status

        # Update the keeper status
        for pick in draft_data['draft_picks']:
            if (pick['player_name'] == player['player_name'] and
                    pick['team_id'] == player['team_id']):
                pick['keeper_status'] = new_status
                break

        # Save the updated data
        with open('data/draft_results.json', 'w') as f:
            json.dump(draft_data, f, indent=2)

        status_text = "keeper" if new_status else "non-keeper"
        print(f"✅ Updated {player['player_name']} to {status_text} status")

    except FileNotFoundError:
        print("❌ Draft results file not found.")
    except Exception as e:
        print(f"❌ Error: {e}")


@app.cli.command()
def keeper_ineligible():
    """Display players who are NOT eligible to be kept for 2025."""
    try:
        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        ineligible = [pick for pick in draft_data['draft_picks']
                      if not pick.get('2025_keeper_eligible', True)]

        if not ineligible:
            print("📋 All players are eligible to be kept for 2025.")
            return

        print("🚫 Players NOT Eligible for 2025 Keepers")
        print("=" * 50)
        ineligible.sort(key=lambda x: x['overall_pick'])

        for player in ineligible:
            team_info = next(team for team in draft_data['teams'] if team['team_id'] == player['team_id'])
            keeper_status = " (2024 Keeper)" if player['keeper_status'] else ""
            print(f"Round {player['round']:2d} (Pick {player['overall_pick']:3d}): {player['player_name']}{keeper_status}")
            print(f"    Team: {player['drafting_team']} (Manager: {team_info['manager']})")

    except FileNotFoundError:
        print("❌ Draft results file not found.")
    except Exception as e:
        print(f"❌ Error: {e}")


@app.cli.command()
def eligible_keepers():
    """Display current 2024 keepers and their 2025 eligibility status."""
    try:
        with open('data/draft_results.json', 'r') as f:
            draft_data = json.load(f)

        keepers = [pick for pick in draft_data['draft_picks'] if pick['keeper_status']]

        if not keepers:
            print("📋 No keepers currently marked in the system.")
            return

        print("🔒 2024 Keepers - 2025 Eligibility Status")
        print("=" * 55)
        keepers.sort(key=lambda x: x['overall_pick'])

        eligible_count = 0
        for keeper in keepers:
            team_info = next(team for team in draft_data['teams'] if team['team_id'] == keeper['team_id'])
            eligibility = "✅ Eligible" if keeper.get('2025_keeper_eligible', True) else "❌ NOT Eligible"
            if keeper.get('2025_keeper_eligible', True):
                eligible_count += 1
            print(f"Round {keeper['round']:2d} (Pick {keeper['overall_pick']:3d}): {keeper['player_name']} - {eligibility}")
            print(f"    Team: {keeper['drafting_team']} (Manager: {team_info['manager']})")

        print(f"\n📊 Summary: {eligible_count}/{len(keepers)} current keepers are eligible for 2025")

    except FileNotFoundError:
        print("❌ Draft results file not found.")
    except Exception as e:
        print(f"❌ Error: {e}")


@app.cli.command()
def keeper_analysis():
    """Generate and display keeper analysis dataframe with 2025 projections."""
    try:
        df = create_keeper_analysis_dataframe()

        if df is None:
            print("❌ Failed to create dataframe")
            return

        print("📊 Keeper Analysis - 2024 vs 2025 Projections")
        print("=" * 80)
        print(f"Total Players: {len(df)}")

        # Show summary statistics
        matched_players = df['2025_draft_rank'].notna().sum()
        print(f"Players with 2025 rankings: {matched_players}/{len(df)}")

        # Show keepers with their 2025 projections
        keepers_df = df[df['2024_keeper_status'] == True].copy()
        if len(keepers_df) > 0:
            print(f"\n🔒 Current Keepers with 2025 Projections:")
            print("-" * 80)
            for _, keeper in keepers_df.iterrows():
                rank_2025 = keeper['2025_draft_rank']
                pos_rank = keeper['2025_position_rank']
                proj_round = keeper['2025_projected_draft_round']
                keeper_round = keeper['2025_keeper_round']
                eligible = "✅" if keeper['2025_keeper_eligible'] else "❌"

                if pd.notna(rank_2025):
                    print(f"{keeper['player_name']:<25} | {keeper['2024_team'][:20]:<20}")
                    print(
                        f"  2024: R{keeper['2024_draft_round']:2d} | 2025: #{rank_2025:3.0f} ({pos_rank}) -> R{proj_round:.0f} | Keeper: R{keeper_round:.0f} {eligible}")
                else:
                    print(f"{keeper['player_name']:<25} | {keeper['2024_team'][:20]:<20}")
                    print(
                        f"  2024: R{keeper['2024_draft_round']:2d} | 2025: Not Ranked | Keeper: R{keeper_round:.0f} {eligible}")

        # Show keeper value analysis
        valuable_keepers = keepers_df[
            (keepers_df['2025_keeper_eligible'] == True) &
            (keepers_df['2025_projected_draft_round'] > keepers_df['2025_keeper_round'])
        ].copy()

        if len(valuable_keepers) > 0:
            print(f"\n💎 Best Keeper Values (2025 proj round > keeper round):")
            print("-" * 50)
            valuable_keepers['keeper_value'] = valuable_keepers['2025_projected_draft_round'] - valuable_keepers['2025_keeper_round']
            valuable_keepers = valuable_keepers.sort_values('keeper_value', ascending=False)

            for _, player in valuable_keepers.head(10).iterrows():
                value = player['keeper_value']
                print(f"{player['player_name']:<25} | +{value:.0f} rounds value")

        print(f"\n💾 Full dataframe available via create_keeper_analysis_dataframe()")

    except Exception as e:
        print(f"❌ Error in keeper analysis: {e}")


@app.route('/')
def keeper_analysis_web():
    """Web interface for keeper analysis with sortable table."""
    try:
        df = create_keeper_analysis_dataframe()

        if df is None:
            return render_template('error.html',
                                   error_message="Failed to load data. Please check that data files exist.")

        # Convert DataFrame to list of dictionaries for template
        # Replace NaN with None so template can handle properly
        df = df.where(pd.notna(df), None)
        players_data = df.to_dict('records')

        # Get unique managers for filter dropdown
        unique_managers = sorted(df['2024_manager'].unique().tolist())

        return render_template('keeper_analysis.html',
                               players=players_data,
                               managers=unique_managers)

    except Exception as e:
        return render_template('error.html',
                               error_message=f"Error generating analysis: {str(e)}")


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'status': 'error'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500


if __name__ == '__main__':
    app.run(
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=int(5001),
        debug=app.config['DEBUG']
    )

from flask import Flask, request, render_template
import pandas as pd
import openai
import os
import logging

app = Flask(__name__)

# Dropbox URLs for the CSV files
URL_CLEAN_DATA = "https://www.dropbox.com/scl/fi/d69weykshmr9vr6g4hqee/clean_data.csv?rlkey=kiixfgpaolg6krxg7z0qg8fg2&st=d6cjmanw&dl=1"
URL_MERGED_DATA = "https://www.dropbox.com/scl/fi/wjgp6xzpzx25fveag5tr3/merged_data.csv?rlkey=gf784pwnefkiyzs22e5v7wjmb&st=pheo6si7&dl=1"
URL_PLAYERS = "https://www.dropbox.com/scl/fi/d999a0r9zypl5z302gdc2/Players.csv?rlkey=coyebnz4ayk5tor75csmyua7r&st=moalwof0&dl=1"

# Load your cleaned player data
df = pd.read_csv(URL_CLEAN_DATA)
additional_df = pd.read_csv(URL_PLAYERS)

# Merge the two dataframes on the 'short_name' column
merged_df = pd.merge(df, additional_df, on='short_name')

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAPIKEY")

def recommended_skills(skill_points, player_attributes):
    recommended_skills = {}
    skill_weights = {key: player_attributes[key] for key in player_attributes if isinstance(player_attributes[key], (int, float))}
    total_weight = sum(skill_weights.values())

    for skill, weight in skill_weights.items():
        recommended_skills[skill] = int(skill_points * (weight / total_weight))
    return recommended_skills

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/build_player", methods=["POST"])
def build_player():
    try:
        player_name = request.form.get("player_description")
        skill_points = int(request.form.get("skill_points"))

        logging.debug(f"Player name: {player_name}")
        logging.debug(f"Skill points: {skill_points}")

        # Fetch player data
        player_data = merged_df[merged_df['long_name'].str.contains(player_name, case=False, na=False)]

        if not player_data.empty:
            player_info = player_data.iloc[0].to_dict()
            rec_skills = recommended_skills(skill_points, player_info)
            
            gpt_prompt = f"The user wants to build a player similar to {player_info['long_name']}. They have {skill_points} skill points. Here is the player's information: Height: {player_info['height_cm']} cm, Weight: {player_info['weight_kg']} kg, Preferred Foot: {player_info['preferred_foot']}, Position: {player_info['club_position']}. Provide a detailed skill point allocation plan to maximize the player's performance, focusing on strengths and weaknesses."

            logging.debug(f"GPT prompt: {gpt_prompt}")

            try:
                client = openai.OpenAI(api_key=openai.api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": gpt_prompt}
                    ]
                )
                gpt_recommendation = response.choices[0].message.content
                logging.debug(f"GPT recommendation: {gpt_recommendation}")

                # Add player info to the recommendation
                player_details = f"Height: {player_info['height_cm']} cm, Weight: {player_info['weight_kg']} kg, Preferred Foot: {player_info['preferred_foot']}"
                full_recommendation = f"<ul>{player_details}</ul><p>{gpt_recommendation}</p>"
            except Exception as e:
                full_recommendation = f"Error generating response: {e}"
                logging.error(f"Error generating GPT response: {e}")

            return render_template('index.html', player_description=player_name, player_info=player_info, gpt_recommendation=full_recommendation)
        else:
            return render_template('index.html', player_description=player_name, gpt_recommendation="Player not found. Please try another name or check the spelling.")
    except Exception as e:
        logging.error(f"Error in build_player function: {e}")
        return render_template('index.html', player_description="", gpt_recommendation=f"An error occurred: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True)

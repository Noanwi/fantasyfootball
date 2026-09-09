from flask import Flask, render_template, request

app = Flask(__name__)

TEAMS = 14


def get_overall_pick(round_number, draft_position, teams=14):
    """
    Calculate the overall pick number for a given round
    in a snake draft.
    """

    if round_number < 1:
        raise ValueError("Round must be at least 1.")

    if not 1 <= draft_position <= teams:
        raise ValueError(
            f"Draft position must be between 1 and {teams}."
        )

    # Odd rounds: normal draft order
    if round_number % 2 == 1:
        pick_in_round = draft_position

    # Even rounds: reversed draft order
    else:
        pick_in_round = teams - draft_position + 1

    overall_pick = ((round_number - 1) * teams) + pick_in_round

    return overall_pick


def get_pick_in_round(round_number, draft_position, teams=14):
    """
    Determine the team's position within a specific round.
    """

    if round_number % 2 == 1:
        return draft_position
    else:
        return teams - draft_position + 1


def get_round_from_pick(overall_pick, draft_position, teams=14):
    """
    Find the latest round whose pick for this team is
    at or before the specified overall pick.

    Returns:
        (round_number, pick_in_round, overall_pick)
    """

    round_number = 1

    while True:
        pick = get_overall_pick(
            round_number,
            draft_position,
            teams
        )

        if pick > overall_pick:

            previous_round = round_number - 1

            if previous_round < 1:
                return None, None, None

            previous_pick = get_overall_pick(
                previous_round,
                draft_position,
                teams
            )

            pick_in_round = get_pick_in_round(
                previous_round,
                draft_position,
                teams
            )

            return (
                previous_round,
                pick_in_round,
                previous_pick
            )

        round_number += 1


def get_next_team_pick(round_number, draft_position, teams=14):
    """
    Calculate the team's next pick after the specified round.

    Returns:
        (next_round, next_pick_in_round, next_overall_pick)
    """

    next_round = round_number + 1

    next_overall_pick = get_overall_pick(
        next_round,
        draft_position,
        teams
    )

    next_pick_in_round = get_pick_in_round(
        next_round,
        draft_position,
        teams
    )

    return (
        next_round,
        next_pick_in_round,
        next_overall_pick
    )


def calculate_keeper_cost(
    drafted_round,
    current_adp,
    draft_position,
    drafted_by_you=True,
    teams=14
):
    """
    Calculate the draft pick required to keep a player.

    Rules:

    1. If you drafted the player yourself last year,
       the base keeper cost is the round you drafted them.

    2. If you did not draft the player yourself last year,
       the base keeper cost is Round 1.

    3. The keeper pick cannot be more than 35 picks
       after the player's current Sleeper ADP.

    4. If the normal keeper pick exceeds the ADP + 35 cap,
       the keeper cost is adjusted to the latest pick
       available to that team that does not exceed the cap.
    """

    # Determine normal keeper round
    if drafted_by_you:
        base_round = drafted_round
    else:
        base_round = 1

    # Determine base overall pick
    base_pick = get_overall_pick(
        base_round,
        draft_position,
        teams
    )

    # Determine position within the round
    base_pick_in_round = get_pick_in_round(
        base_round,
        draft_position,
        teams
    )

    # ADP + 35 is the absolute ceiling
    maximum_allowed_pick = current_adp + 35

    # Normal keeper pick is within the cap
    if base_pick <= maximum_allowed_pick:

        keeper_round = base_round
        keeper_pick_in_round = base_pick_in_round
        keeper_pick = base_pick
        adjusted = False

    # Normal keeper pick exceeds the cap
    else:

        (
            keeper_round,
            keeper_pick_in_round,
            keeper_pick
        ) = get_round_from_pick(
            maximum_allowed_pick,
            draft_position,
            teams
        )

        adjusted = True

    # Calculate next pick
    (
        next_round,
        next_pick_in_round,
        next_pick
    ) = get_next_team_pick(
        keeper_round,
        draft_position,
        teams
    )

    # Difference between keeper pick and ADP
    difference = keeper_pick - current_adp

    return {
        "base_round": base_round,
        "base_pick_in_round": base_pick_in_round,
        "base_pick": base_pick,
        "current_adp": current_adp,
        "maximum_allowed_pick": maximum_allowed_pick,

        "keeper_round": keeper_round,
        "keeper_pick_in_round": keeper_pick_in_round,
        "keeper_pick": keeper_pick,

        "adjusted": adjusted,

        "next_round": next_round,
        "next_pick_in_round": next_pick_in_round,
        "next_pick": next_pick,

        "difference": difference
    }


@app.route("/", methods=["GET", "POST"])
def index():

    result = None
    error = None

    form_data = {
        "player_name": "",
        "drafted_round": "",
        "current_adp": "",
        "draft_position": "",
        "drafted_by_you": "yes"
    }

    if request.method == "POST":

        form_data = {
            "player_name": request.form.get(
                "player_name", ""
            ).strip(),

            "drafted_round": request.form.get(
                "drafted_round", ""
            ),

            "current_adp": request.form.get(
                "current_adp", ""
            ),

            "draft_position": request.form.get(
                "draft_position", ""
            ),

            "drafted_by_you": request.form.get(
                "drafted_by_you", "yes"
            )
        }

        try:

            player_name = form_data["player_name"]

            if not player_name:
                raise ValueError(
                    "Please enter a player's name."
                )

            drafted_round = int(
                form_data["drafted_round"]
            )

            current_adp = float(
                form_data["current_adp"]
            )

            draft_position = int(
                form_data["draft_position"]
            )

            if drafted_round < 1:
                raise ValueError(
                    "Drafted round must be at least 1."
                )

            if current_adp < 0:
                raise ValueError(
                    "ADP cannot be negative."
                )

            if not 1 <= draft_position <= TEAMS:
                raise ValueError(
                    f"Draft position must be between 1 and {TEAMS}."
                )

            drafted_by_you = (
                form_data["drafted_by_you"] == "yes"
            )

            result = calculate_keeper_cost(
                drafted_round=drafted_round,
                current_adp=current_adp,
                draft_position=draft_position,
                drafted_by_you=drafted_by_you,
                teams=TEAMS
            )

            # Add player name to result
            result["player_name"] = player_name

        except ValueError as e:

            error = str(e)

    return render_template(
        "index.html",
        result=result,
        error=error,
        form_data=form_data,
        teams=TEAMS
    )


if __name__ == "__main__":
    app.run(debug=True)
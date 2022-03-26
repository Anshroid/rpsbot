import random

import discord
import asyncio

# Initialize the bot
client = discord.Client(intents=discord.Intents.all())

with open("token.env", "r") as f:
    TOKEN = f.read()

# Stores running games and rematch requests
rps = []
rematches = []

# Stores winning combinations
combos = {
    "🪨": {
        "🪨": None,
        "🧻": False,
        "✂️": True
    },

    "🧻": {
        "🪨": True,
        "🧻": None,
        "✂️": False
    },
    "✂️": {
        "🪨": False,
        "🧻": True,
        "✂️": None
    },
}


# A function to automatically delete rematch messages after a certain amount of time
async def delete_after(message, seconds, evt):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except discord.errors.NotFound:
        pass  # message was already deleted because rematch was accepted
    evt.set()


# The main function
@client.event
async def on_message(message, ng=True):
    # When a new message is sent that starts with !rps
    if message.content.startswith("!rps"):

        # Store the players in the game
        try:
            players = [message.author, message.mentions[0]]
        except IndexError:
            # If there are no mentions, the game is cancelled
            await message.channel.send("You need to play with someone....")
            return

        # If the player tries to play with themselves, the game is cancelled
        if players[0] == players[1]:
            await message.channel.send("Are you alone? :(")
            return

        # Try to delete the initial message
        try:
            await message.delete()
            ng = True  # If the message was deleted, the game is new
        except discord.errors.NotFound:
            ng = False  # If the message wasn't deleted, the game is not new
            pass  # message was already deleted and this is a rematch

        # Only say the game is new if it just started
        if ng:
            await message.channel.send(f"A game has begun between " +
                                       f"{players[0].name} and {players[1].name}!")

        # Display the typing indicator
        async with message.channel.typing():
            for player in players:
                # Create a dm with each player if they don't have one
                if (not player.bot) and player.dm_channel is None:
                    await player.create_dm()

                # Send the game message to each player
                if not player.bot:
                    # Clear out any old messages e.g. if the bot was restarted or crashed
                    async for msg in player.dm_channel.history():
                        if msg.author == client.user:
                            await msg.delete()

                    # Send the game message
                    await player.dm_channel.send("Choose an option!")

            # Store the game in the list of running games
            rps.append(((asyncio.Event(), asyncio.Event()),  # Keeps track of who has responded
                        (players[0], players[1]),            # Keeps track of who is playing
                        [0, 0]))                             # Keeps track of the chosen options

            # Remember which game is related to this message
            idx = len(rps) - 1

            # If the bot is one of the players, it will choose a random option
            if client.user in players:
                # Only say I am choosing if it's a new game
                if ng:
                    await message.channel.send(f"You are playing against meeeeee! ")

                # Set the event to show that the bot has chosen
                rps[idx][0][players.index(client.user)].set()
                # Choose a random option
                rps[idx][2][players.index(client.user)] = random.choice(["🪨", "🧻", "✂️"])

            # Wait for the players to respond
            for evt in rps[idx][0]:
                await evt.wait()

        # Use the chosen options to determine the winner
        winner = 0 if combos[rps[idx][2][0]][rps[idx][2][1]] is True else \
            (1 if combos[rps[idx][2][0]][rps[idx][2][1]] is False else 2)

        # If the game is a draw, say so
        if winner == 2:
            await message.channel.send(
                f"{rps[idx][2][0]} It's a draw! {rps[idx][2][1]}"
            )
        else:
            # If the game is won, say who won
            await message.channel.send(
                f"{rps[idx][2][winner]} " +
                f"{rps[idx][1][winner].name} Wins! " +
                f"{rps[idx][2][winner - 1]}"
            )

        # Store the new rematch request
        rematches.append(((asyncio.Event(), asyncio.Event()),  # Keeps track of who has responded
                          (players[0], players[1]),            # Keeps track of who is participating
                          [0, 0]))                             # Keeps track of the chosen options

        # If the bot is one of the players, automatically accept the rematch
        if client.user in players:
            # Set the event to show that the bot has chosen
            rematches[-1][0][players.index(client.user)].set()
            # Accept the rematch
            rematches[-1][2][players.index(client.user)] = 1

        # Send the rematch request to each player
        for player in players:
            if not player.bot:
                # Construct the message to tell the player who won
                win_text = "It's a draw!" if winner == 2 else \
                    "You won!" if rps[idx][1][winner] == player else \
                    "You lost!"

                # Send the message and wait for a response for 10 seconds, and then delete it
                asyncio.create_task(delete_after(await player.dm_channel.send(f"{win_text} Play again?"), 10,
                                                 rematches[-1][0][players.index(player)]))

        # Remove the game from the list of running games
        del rps[idx]

        # Keep track of which rematch is related to this message
        idx = len(rematches) - 1

        # Wait for the players to respond
        for evt in rematches[idx][0]:
            await evt.wait()

        # If both players accepted the rematch, start a new game
        if rematches[idx][2] == [1, 1]:
            del rematches[idx]  # Remove the rematch request from the list of running rematches
            await on_message(message)  # Just call the on_message function again and pretend the command was rerun
        else:
            # If one of the players declined, remove the rematch request from the list of running rematches anyway
            del rematches[idx]

    # If this is a message that the bot sent instead
    elif message.author == client.user:
        # If the message is requesting a game, add the reactions to the message
        if message.content == "Choose an option!":
            await message.add_reaction("🪨")
            await message.add_reaction("🧻")
            await message.add_reaction("✂️")

        # If the message is requesting a rematch, add the reactions to the message
        elif message.content.endswith("Play again?"):
            await message.add_reaction("✅")
            await message.add_reaction("❌")


# This function is called when a reaction is added to a message
@client.event
async def on_reaction_add(reaction, user):
    # If it's a reaction to a message that the bot sent, and it isn't the bots own reaction
    if reaction.message.author == client.user and user != client.user:
        # If it is a reaction to a game message
        if reaction.message.content == "Choose an option!":
            # If it is one of the choices
            if reaction.emoji in "🪨🧻✂️":
                # Try and find the game in reference to the message
                for game in rps:
                    if user in game[1]:
                        # If the game is found, store the choice
                        game[2][game[1].index(user)] = reaction.emoji
                        # Record that the player has chosen
                        game[0][game[1].index(user)].set()

                        # Debug log the choice
                        print(f"{user.name} picked {reaction.emoji}!")

                        # Delete the game message
                        await reaction.message.delete()
                        break

        # If it is instead a rematch message reaction
        elif reaction.message.content.endswith("Play again?"):
            # If it is a yes or no reaction
            if reaction.emoji in "✅❌":
                # Try and find the rematch in reference to the message
                for rematch in rematches:
                    if user in rematch[1]:
                        # If the rematch is found, store the choice
                        rematch[2][rematch[1].index(user)] = 1 if reaction.emoji == "✅" else 0
                        # Record that the player has chosen
                        rematch[0][rematch[1].index(user)].set()

                        # Log the choice
                        print(f"{user.name} {'wants' if reaction.emoji == '✅' else 'does not want'} to play again!")

                        # Delete the rematch message
                        await reaction.message.delete()
                        break

# Run the bot
client.run(TOKEN)

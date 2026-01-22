# KingFifer40's Clean Memes Bot Description
This is my Bot's code that I use in a Groupme group called "Clean Memes". It uses an account token, so in order to use it, you need to go to dev.groupme.com and get the token and place it in there. You also need to find the id of the group/topic you will put it in, and place it in the config on top. I will continually update it and potentially add more features.

# Groupme Token guide
1. Open dev.groupme.com
2. Sign into your groupme account
3. Click the "Access Token" button in the top right corner of the website
4. Copy that into the script where the TOKEN variable is, in between the parenthesis, replacing the text inside.

# Groupme Group ID guide
1. Open web.groupme.com on a PC
2. Sign into your groupme account
3. Navigate to the group you would like to place your bot in
4. locate the main topic, open it, and then right-click and press inspect, or press f12 or whatever shortcut opens devtools
5. Open the network tab
6. Send a message or react to one in the topic, watching the network and should you react, find a "Like" request in the log, or if it is a message that you sent, find the "Messages" request in the log. There are always two of these, so click one, as it does not matter the one you click on
7. Look at the details to the request you are inspecting. Locate something that looks like /v3/groups/TOPIC_NUMBER/messages, but instead of TOPIC_NUMBER, you will find a 9-digit number. This is the id of the main topic, which should be pasted into the parenthesis of the variable MAIN_GROUP_ID in the script.

# Groupme Group ID where it interacts
The GROUP_ID variable is the group/topic where the bot can interact with users. This may be changed to work in all topics of one group in the future, but for now it shall be one topic. You would need to follow the last steps to get the id of this group, and it does not need to be the main topic.

There are features not yet used in this script that may be fully implemented later.

from db import *

from quotes import *

from config import users_from_database

from email_sender import *

init_db()



for user in users_from_database:
    add_user(
        user["email"], user["name"], user["subscription_status"], user["email_frequency"]
    )

# sub = get_eligible_subscribers()
# print(sub[0])
# print(sub[1])
# print(type(sub))

# add_user("faruksedik@yahoo.com", name="Faruk", subscription_status="active", email_frequency="daily")
# add_user("faruksedik@gmail.com", name="Babatunde", subscription_status="active", email_frequency="daily")

# daily_users = get_active_subscribers()
# print(f"Found {len(daily_users)} active daily subscribers.")

# quotes_list = fetch_quotes()

daily_quotes_list_saved = [{'q': 'Walk slowly but never walk backward.',
  'a': 'Unknown',
  'c': '36',
  'h': '<blockquote>&ldquo;Walk slowly but never walk backward.&rdquo; &mdash; <footer>Unknown</footer></blockquote>'},
 {'q': 'Great minds discuss ideas. Average minds discuss events. Small minds discuss people.',
  'a': 'Eleanor Roosevelt',
  'c': '84',
  'h': '<blockquote>&ldquo;Great minds discuss ideas. Average minds discuss events. Small minds discuss people.&rdquo; &mdash; <footer>Eleanor Roosevelt</footer></blockquote>'},
 {'q': 'Quality is more important than quantity. One home run is much better than two doubles.',
  'a': 'Steve Jobs',
  'c': '86',
  'h': '<blockquote>&ldquo;Quality is more important than quantity. One home run is much better than two doubles.&rdquo; &mdash; <footer>Steve Jobs</footer></blockquote>'},
 {'q': 'We will now discuss in a little more detail the Struggle for Existence.',
  'a': 'Charles Darwin',
  'c': '71',
  'h': '<blockquote>&ldquo;We will now discuss in a little more detail the Struggle for Existence.&rdquo; &mdash; <footer>Charles Darwin</footer></blockquote>'},
 {'q': 'Time heals what reason cannot.  ',
  'a': 'Seneca',
  'c': '32',
  'h': '<blockquote>&ldquo;Time heals what reason cannot.  &rdquo; &mdash; <footer>Seneca</footer></blockquote>'},
 {'q': "People who have goals succeed because they know where they're going. It's that simple.",
  'a': 'Earl Nightingale',
  'c': '86',
  'h': "<blockquote>&ldquo;People who have goals succeed because they know where they're going. It's that simple.&rdquo; &mdash; <footer>Earl Nightingale</footer></blockquote>"},
 {'q': 'We are most nearly ourselves when we achieve the seriousness of the child at play.',
  'a': 'Heraclitus',
  'c': '82',
  'h': '<blockquote>&ldquo;We are most nearly ourselves when we achieve the seriousness of the child at play.&rdquo; &mdash; <footer>Heraclitus</footer></blockquote>'},
 {'q': "The whole world is a series of miracles, but we're so used to them we call them ordinary things.",
  'a': 'Hans Christian Andersen',
  'c': '96',
  'h': "<blockquote>&ldquo;The whole world is a series of miracles, but we're so used to them we call them ordinary things.&rdquo; &mdash; <footer>Hans Christian Andersen</footer></blockquote>"},
 {'q': 'Believe in yourself. You are braver than you think, more talented than you know, and capable of more than you imagine.',
  'a': 'Roy T. Bennett',
  'c': '118',
  'h': '<blockquote>&ldquo;Believe in yourself. You are braver than you think, more talented than you know, and capable of more than you imagine.&rdquo; &mdash; <footer>Roy T. Bennett</footer></blockquote>'},
 {'q': "It doesn't matter how much you want. What really matters is how much you want it.",
  'a': 'Ralph Marston',
  'c': '81',
  'h': "<blockquote>&ldquo;It doesn't matter how much you want. What really matters is how much you want it.&rdquo; &mdash; <footer>Ralph Marston</footer></blockquote>"}]

quotes_list = []

for item in daily_quotes_list_saved[:10]:
        if "q" in item and "a" in item:
            quotes_list.append({
                "quote": item["q"],
                "author": item.get("a", "Unknown")
            })


# send_daily_quotes(quotes_list)
# send_weekly_quotes(quotes_list)

send_emails_to_subscribers("daily", quotes_list)

send_summary_to_admin()
# random_quote = get_random_quote(quotes_list)

# print(random_quote)
# import emailer
# quote = {"text": "keep on learning you will get there soon.", "author": "FARUK SEDIK"}
# emailer.send_email_with_retries(daily_users[1], quote)

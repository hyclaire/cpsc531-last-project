from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup

# Flask app setup
app = Flask(__name__)

# MongoDB Atlas Configuration
#MONGO_URI = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/dbname?tls=true&tlsAllowInvalidCertificates=true"
client = MongoClient(MONGO_URI)
db = client.newsDB  # Database name
collection = db.articles  # Collection name

# NewsAPI Configuration
NEWS_API_KEY = "f3a094f995904af195df8a9c9e45406e"  # Replace with your API key
NEWS_API_URL = "https://newsapi.org/v2/everything"

SCRAPE_URL = "https://www.bbc.com/news"  # Example news website to scrape

@app.route('/collect', methods=['GET'])
def collect_articles():
    # Get the query parameter from the request (default: 'technology')
    query = request.args.get('query')
    print(f"Fetching articles for query: {query}")

    # Request parameters for NewsAPI
    params = {
        'q': query,
        'apiKey': NEWS_API_KEY,
        'pageSize': 5,
        'sortBy': 'publishedAt'
    }
    response = requests.get(NEWS_API_URL, params=params)
    print(f"API Response Status Code: {response.status_code}")
    
    # Fetch articles from NewsAPI
    response = requests.get(NEWS_API_URL, params=params)
    if response.status_code != 200:
        return jsonify({
            'error': response.json().get('message', 'Unknown error'),
            'status_code': response.status_code
        })

    articles = response.json().get('articles', [])
    print(f"Fetched {len(articles)} articles.")
    
    saved_articles = []
    for article in articles:
        article_data = {
            'title': article['title'],
            'description': article['description'],
            'url': article['url'],
            'publishedAt': article['publishedAt'],
            'source': article['source']['name']
        }
        try:
            if collection.find_one({'url': article['url']}) is None:
                collection.insert_one(article_data)
                saved_articles.append(article_data)
                print(f"Article inserted: {article['title']}")
            else:
                print(f"Duplicate article skipped: {article['title']}")
        except Exception as e:
            print(f"Error inserting article: {e}")

    return jsonify({
        'message': f'{len(saved_articles)} new articles saved.',
        'saved_articles': saved_articles
    })

@app.route('/collect/scraping', methods=['GET'])
def collect_articles_from_scraping():
    """
    Scrape news articles from a website and store them in MongoDB.
    """
    response = requests.get(SCRAPE_URL)

    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch the website content'})

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('a', class_='gs-c-promo-heading')  # Adjust selector for the target website

    saved_articles = []

    for article in articles:
        title = article.get_text()
        url = article['href']
        if not url.startswith("http"):
            url = f"https://www.bbc.com{url}"  # Append domain for relative URLs

        if collection.find_one({'url': url}) is None:  # Check for duplicates
            article_data = {
                'title': title,
                'url': url,
                'source': 'BBC News',  # Update with the appropriate source
                'source_type': 'web_scraping'
            }
            collection.insert_one(article_data)
            saved_articles.append(article_data)

    return jsonify({
        'message': f'{len(saved_articles)} articles saved from web scraping.',
        'saved_articles': saved_articles
    })

@app.route('/news')
def news():
    # Fetch news articles from MongoDB
    articles = collection.find()  # This assumes articles are stored in MongoDB
    articles_list = []
    for article in articles:
        articles_list.append({
            'title': article['title'],
            'url': article['url'],
            'description': article.get('description', 'No description available')
        })
    return render_template('news.html', articles=articles_list)

@app.route('/')
def index():
    username = request.cookies.get('username')
    if username:
        return "Home page is working"
    else:
        return redirect(url_for('profile'))
    if request.method == 'POST':
        username = request.form['username']
        if'_' not in username:
            return "Not a Valid Username"
    resp = make_response(redirect(url_for('profile')))
    resp
    import argparse
    import gym
    import numpy as np
    from itertools import count
    from collections import namedtuple
    
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    from torch.distributions import Categorical
    
    # Cart Pole
    
    parser = argparse.ArgumentParser(description='PyTorch actor-critic example')
    parser.add_argument('--gamma', type=float, default=0.99, metavar='G',
                        help='discount factor (default: 0.99)')
    parser.add_argument('--seed', type=int, default=543, metavar='N',
                        help='random seed (default: 543)')
    parser.add_argument('--render', action='store_true',
                        help='render the environment')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='interval between training status logs (default: 10)')
    args = parser.parse_args()
    
    
    env = gym.make('CartPole-v0')
    env.seed(args.seed)
    torch.manual_seed(args.seed)
    
    
    SavedAction = namedtuple('SavedAction', ['log_prob', 'value'])
    
    
    class Policy(nn.Module):
        """
        implements both actor and critic in one model
        """
        def __init__(self):
            super(Policy, self).__init__()
            self.affine1 = nn.Linear(4, 128)
    
            # actor's layer
            self.action_head = nn.Linear(128, 2)
    
            # critic's layer
            self.value_head = nn.Linear(128, 1)
    
            # action & reward buffer
            self.saved_actions = []
            self.rewards = []
    
        def forward(self, x):
            """
            forward of both actor and critic
            """
            x = F.relu(self.affine1(x))
    
            # actor: choses action to take from state s_t
            # by returning probability of each action
            action_prob = F.softmax(self.action_head(x), dim=-1)
    
            # critic: evaluates being in the state s_t
            state_values = self.value_head(x)
    
            # return values for both actor and critic as a tupel of 2 values:
            # 1. a list with the probability of each action over the action space
            # 2. the value from state s_t
            return action_prob, state_values
    
    
    model = Policy()
    optimizer = optim.Adam(model.parameters(), lr=3e-2)
    eps = np.finfo(np.float32).eps.item()
    
    
    def select_action(state):
        state = torch.from_numpy(state).float()
        probs, state_value = model(state)
    
        # create a categorical distribution over the list of probabilities of actions
        m = Categorical(probs)
    
        # and sample an action using the distribution
        action = m.sample()
    
        # save to action buffer
        model.saved_actions.append(SavedAction(m.log_prob(action), state_value))
    
        # the action to take (left or right)
        return action.item()
    
    
    def finish_episode():
        """
        Training code. Calcultes actor and critic loss and performs backprop.
        """
        R = 0
        saved_actions = model.saved_actions
        policy_losses = [] # list to save actor (policy) loss
        value_losses = [] # list to save critic (value) loss
        returns = [] # list to save the true values
    
        # calculate the true value using rewards returned from the environment
        for r in model.rewards[::-1]:
            # calculate the discounted value
            R = r + args.gamma * R
            returns.insert(0, R)
    
        returns = torch.tensor(returns)
        returns = (returns - returns.mean()) / (returns.std() + eps)
    
        for (log_prob, value), R in zip(saved_actions, returns):
            advantage = R - value.item()
    
            # calculate actor (policy) loss
            policy_losses.append(-log_prob * advantage)
    
            # calculate critic (value) loss using L1 smooth loss
            value_losses.append(F.smooth_l1_loss(value, torch.tensor([R])))
    
        # reset gradients
        optimizer.zero_grad()
    
        # sum up all the values of policy_losses and value_losses
        loss = torch.stack(policy_losses).sum() + torch.stack(value_losses).sum()
    
        # perform backprop
        loss.backward()
        optimizer.step()
    
        # reset rewards and action buffer
        del model.rewards[:]
        del model.saved_actions[:]
    
    
    def main():
        running_reward = 10
    
        # run inifinitely many episodes
        for i_episode in count(1):
    
            # reset environment and episode reward
            state = env.reset()
            ep_reward = 0
    
            # for each episode, only run 9999 steps so that we don't
            # infinite loop while learning
            for t in range(1, 10000):
    
                # select action from policy
                action = select_action(state)
    
                # take the action
                state, reward, done, _ = env.step(action)
    
                if args.render:
                    env.render()
    
                model.rewards.append(reward)
                ep_reward += reward
                if done:
                    break
    
            # update cumulative reward
            running_reward = 0.05 * ep_reward + (1 - 0.05) * running_reward
    
            # perform backprop
            finish_episode()
    
            # log results
            if i_episode % args.log_interval == 0:
                print('Episode {}\tLast reward: {:.2f}\tAverage reward: {:.2f}'.format(
                      i_episode, ep_reward, running_reward))
    
            # check if we have "solved" the cart pole problem
            if running_reward > env.spec.reward_threshold:
                print("Solved! Running reward is now {} and "
                      "the last episode runs to {} time steps!".format(running_reward, t))
                break
    
    
    if __name__ == '__main__':
        main()
    import argparse
    import gym
    import numpy as np
    from itertools import count
    from collections import namedtuple
    
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    from torch.distributions import Categorical
    
    # Cart Pole
    
    parser = argparse.ArgumentParser(description='PyTorch actor-critic example')
    parser.add_argument('--gamma', type=float, default=0.99, metavar='G',
                        help='discount factor (default: 0.99)')
    parser.add_argument('--seed', type=int, default=543, metavar='N',
                        help='random seed (default: 543)')
    parser.add_argument('--render', action='store_true',
                        help='render the environment')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='interval between training status logs (default: 10)')
    args = parser.parse_args()
    
    
    env = gym.make('CartPole-v0')
    env.seed(args.seed)
    torch.manual_seed(args.seed)
    
    
    SavedAction = namedtuple('SavedAction', ['log_prob', 'value'])
    
    
    class Policy(nn.Module):
        """
        implements both actor and critic in one model
        """
        def __init__(self):
            super(Policy, self).__init__()
            self.affine1 = nn.Linear(4, 128)
    
            # actor's layer
            self.action_head = nn.Linear(128, 2)
    
            # critic's layer
            self.value_head = nn.Linear(128, 1)
    
            # action & reward buffer
            self.saved_actions = []
            self.rewards = []
    
        def forward(self, x):
            """
            forward of both actor and critic
            """
            x = F.relu(self.affine1(x))
    
            # actor: choses action to take from state s_t
            # by returning probability of each action
            action_prob = F.softmax(self.action_head(x), dim=-1)
    
            # critic: evaluates being in the state s_t
            state_values = self.value_head(x)
    
            # return values for both actor and critic as a tupel of 2 values:
            # 1. a list with the probability of each action over the action space
            # 2. the value from state s_t
            return action_prob, state_values
    
    
    model = Policy()
    optimizer = optim.Adam(model.parameters(), lr=3e-2)
    eps = np.finfo(np.float32).eps.item()
    
    
    def select_action(state):
        state = torch.from_numpy(state).float()
        probs, state_value = model(state)
    
        # create a categorical distribution over the list of probabilities of actions
        m = Categorical(probs)
    
        # and sample an action using the distribution
        action = m.sample()
    
        # save to action buffer
        model.saved_actions.append(SavedAction(m.log_prob(action), state_value))
    
        # the action to take (left or right)
        return action.item()
    
    
    def finish_episode():
        """
        Training code. Calcultes actor and critic loss and performs backprop.
        """
        R = 0
        saved_actions = model.saved_actions
        policy_losses = [] # list to save actor (policy) loss
        value_losses = [] # list to save critic (value) loss
        returns = [] # list to save the true values
    
        # calculate the true value using rewards returned from the environment
        for r in model.rewards[::-1]:
            # calculate the discounted value
            R = r + args.gamma * R
            returns.insert(0, R)
    
        returns = torch.tensor(returns)
        returns = (returns - returns.mean()) / (returns.std() + eps)
    
        for (log_prob, value), R in zip(saved_actions, returns):
            advantage = R - value.item()
    
            # calculate actor (policy) loss
            policy_losses.append(-log_prob * advantage)
    
            # calculate critic (value) loss using L1 smooth loss
            value_losses.append(F.smooth_l1_loss(value, torch.tensor([R])))
    
        # reset gradients
        optimizer.zero_grad()
    
        # sum up all the values of policy_losses and value_losses
        loss = torch.stack(policy_losses).sum() + torch.stack(value_losses).sum()
    
        # perform backprop
        loss.backward()
        optimizer.step()
    
        # reset rewards and action buffer
        del model.rewards[:]
        del model.saved_actions[:]
    
    
    def main():
        running_reward = 10
    
        # run inifinitely many episodes
        for i_episode in count(1):
    
            # reset environment and episode reward
            state = env.reset()
            ep_reward = 0
    
            # for each episode, only run 9999 steps so that we don't
            # infinite loop while learning
            for t in range(1, 10000):
    
                # select action from policy
                action = select_action(state)
    
                # take the action
                state, reward, done, _ = env.step(action)
    
                if args.render:
                    env.render()
    
                model.rewards.append(reward)
                ep_reward += reward
                if done:
                    break
    
            # update cumulative reward
            running_reward = 0.05 * ep_reward + (1 - 0.05) * running_reward
    
            # perform backprop
            finish_episode()
    
            # log results
            if i_episode % args.log_interval == 0:
                print('Episode {}\tLast reward: {:.2f}\tAverage reward: {:.2f}'.format(
                      i_episode, ep_reward, running_reward))
    
            # check if we have "solved" the cart pole problem
            if running_reward > env.spec.reward_threshold:
                print("Solved! Running reward is now {} and "
                      "the last episode runs to {} time steps!".format(running_reward, t))
                break
    
    
    if __name__ == '__main__':
        main()


if __name__ == '__main__':
    app.run(debug=True)

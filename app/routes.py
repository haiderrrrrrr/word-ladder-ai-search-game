import random
import os
import io
import base64
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
from heapq import heappop, heappush
from collections import deque
from flask import render_template, request, jsonify, redirect, url_for, session
from app import app
matplotlib.use('Agg')  # Use non-GUI backend

app.secret_key = os.environ.get("SECRET_KEY", "word-ladder-dev-secret")

# Load valid 3-letter words from '3.txt'
def load_valid_words():
    file_path = os.path.join(os.getcwd(), 'app', '3.txt')  # Correct file path
    with open(file_path, 'r') as file:
        valid_words = set(word.strip().lower() for word in file.readlines())
    return valid_words

# Load valid 5-letter words from '5.txt'
def load_advanced_words():
    file_path = os.path.join(os.getcwd(), 'app', '5.txt')  # Correct file path
    with open(file_path, 'r') as file:
        advanced_words = set(word.strip().lower() for word in file.readlines())
    return advanced_words

# Load banned words from 'banned.txt'
# Load valid 6-letter words from '6.txt'
def load_expert_words():
    file_path = os.path.join(os.getcwd(), 'app', '6.txt')
    with open(file_path, 'r') as file:
        expert_words = set(word.strip().lower() for word in file.readlines())
    return expert_words

# Now load the words at the start:
expert_words = load_expert_words()


valid_words = load_valid_words()
advanced_words = load_advanced_words()

# Validate if a word exists in the dictionary
def validate_word(word, mode):
    if mode == "beginner":
        return word in valid_words
    elif mode == "advanced":
        return word in advanced_words
    elif mode == "expert":
        return word in expert_words
    return False

# Generate a random word from the valid words set
def generate_random_word(mode):
    if mode == "beginner":
        return random.choice(list(valid_words))
    elif mode == "advanced":
        return random.choice(list(advanced_words))
    elif mode == "expert":
        return random.choice(list(expert_words))
    return ""


# Get all possible words by changing one letter
def get_neighbors(word, mode):
    neighbors = []
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    for i in range(len(word)):
        for letter in alphabet:
            new_word = word[:i] + letter + word[i+1:]
            if new_word != word and validate_word(new_word, mode):
                neighbors.append(new_word)
    return neighbors

# Breadth-First Search (BFS) for shortest transformation path
def bfs(start_word, end_word, mode):
    queue = deque([[start_word]])
    visited = set([start_word])

    while queue:
        path = queue.popleft()
        current_word = path[-1]

        if current_word == end_word:
            return path

        for neighbor in get_neighbors(current_word, mode):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return []

# Uniform Cost Search (UCS) for shortest transformation path
def ucs(start_word, end_word, mode):
    queue = []
    heappush(queue, (0, [start_word]))
    visited = set([start_word])

    while queue:
        cost, path = heappop(queue)
        current_word = path[-1]

        if current_word == end_word:
            return path

        for neighbor in get_neighbors(current_word, mode):
            if neighbor not in visited:
                visited.add(neighbor)
                heappush(queue, (cost + 1, path + [neighbor]))

    return []

# A* Search for shortest transformation path
def a_star(start_word, end_word, mode):
    def heuristic(word):
        return sum(1 for a, b in zip(word, end_word) if a != b)

    queue = []
    heappush(queue, (0 + heuristic(start_word), 0, [start_word]))  # (f(n), cost, path)
    visited = set([start_word])

    while queue:
        _, cost, path = heappop(queue)
        current_word = path[-1]

        if current_word == end_word:
            return path

        for neighbor in get_neighbors(current_word, mode):
            if neighbor not in visited:
                visited.add(neighbor)
                heappush(queue, (cost + 1 + heuristic(neighbor), cost + 1, path + [neighbor]))

    return []

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/start_game')
def start_game():
    return render_template('difficulty.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/game_rules')
def game_rules():
    return render_template('game_rules.html')

@app.route('/game/choose_mode/<mode>')
def choose_mode(mode):
    if mode == "beginner":
        return redirect(url_for('beginner_mode'))
    elif mode == "advanced":
        return redirect(url_for('advanced_mode'))
    elif mode == "expert":
        return redirect(url_for('expert_mode'))
    return f"Selected Mode: {mode.capitalize()}"


@app.route('/beginner_mode', methods=['GET', 'POST'])
def beginner_mode():
    error_message = None
    success_message = None
    mode = "beginner"

    # Initialize score if not already set
    if 'beginner_score' not in session:
        session['beginner_score'] = 10

    # Ensure session keys exist for words
    if 'beginner_start_word' not in session or 'beginner_end_word' not in session:
        session['beginner_start_word'] = generate_random_word(mode)
        session['beginner_end_word'] = generate_random_word(mode)

    start_word = session['beginner_start_word']
    end_word = session['beginner_end_word']

    if request.method == 'POST':
        user_input = request.form.get('user_input').lower()

        if len(user_input) != 3:
            error_message = "Input word must be exactly 3 letters long."
            session['beginner_score'] -= 5
        elif not validate_word(user_input, mode):
            error_message = "Invalid word entered. Please try again."
            session['beginner_score'] -= 5
        else:
            changes = sum(1 for a, b in zip(start_word, user_input) if a != b)
            if changes != 1:
                error_message = "You must change exactly one letter."
                session['beginner_score'] -= 5
            else:
                # Valid move: add points
                session['beginner_score'] += 10
                if user_input == end_word:
                    success_message = "Success! You reached the end word!"
                    # Remove old words so new ones are generated
                    session.pop('beginner_start_word', None)
                    session.pop('beginner_end_word', None)
                else:
                    session['beginner_start_word'] = user_input  # Update start word

        # If words have been popped, generate new ones
        if 'beginner_start_word' not in session or 'beginner_end_word' not in session:
            session['beginner_start_word'] = generate_random_word(mode)
            session['beginner_end_word'] = generate_random_word(mode)

        return render_template('beginner.html',
                               start_word=session['beginner_start_word'],
                               end_word=session['beginner_end_word'],
                               success_message=success_message,
                               error_message=error_message,
                               score=session['beginner_score'])

    return render_template('beginner.html',
                           start_word=start_word,
                           end_word=end_word,
                           score=session['beginner_score'])

@app.route('/advanced_mode', methods=['GET', 'POST'])
def advanced_mode():
    error_message = None
    success_message = None
    mode = "advanced"

    # Initialize score if not already set
    if 'advanced_score' not in session:
        session['advanced_score'] = 50  # Initial score is now 50

    # Ensure session keys exist for words with valid path
    if 'advanced_start_word' not in session or 'advanced_end_word' not in session:
        start_word, end_word = None, None
        while True:
            start_word = generate_random_word(mode)
            end_word = generate_random_word(mode)
            if bfs(start_word, end_word, mode):  # Ensure a valid path exists
                break
        session['advanced_start_word'] = start_word
        session['advanced_end_word'] = end_word

    start_word = session['advanced_start_word']
    end_word = session['advanced_end_word']

    if request.method == 'POST':
        user_input = request.form.get('user_input').lower()

        if len(user_input) != 5:
            error_message = "Input word must be exactly 5 letters long."
            session['advanced_score'] -= 45
        elif not validate_word(user_input, mode):
            error_message = "Invalid word entered. Please try again."
            session['advanced_score'] -= 45
        else:
            changes = sum(1 for a, b in zip(start_word, user_input) if a != b)
            if changes != 1:
                error_message = "You must change exactly one letter."
                session['advanced_score'] -= 45
            else:
                # Valid move: add points
                session['advanced_score'] += 50
                if user_input == end_word:
                    success_message = "Success! You reached the end word!"
                    # Remove old words so new ones are generated with a valid path
                    session.pop('advanced_start_word', None)
                    session.pop('advanced_end_word', None)
                else:
                    session['advanced_start_word'] = user_input  # Update start word

        # If words have been popped, generate new ones with valid path
        if 'advanced_start_word' not in session or 'advanced_end_word' not in session:
            while True:
                start_word = generate_random_word(mode)
                end_word = generate_random_word(mode)
                if bfs(start_word, end_word, mode):  # Ensure a valid path exists
                    break
            session['advanced_start_word'] = start_word
            session['advanced_end_word'] = end_word

        return render_template('advanced.html',
                               start_word=session['advanced_start_word'],
                               end_word=session['advanced_end_word'],
                               success_message=success_message,
                               error_message=error_message,
                               score=session['advanced_score'])

    return render_template('advanced.html',
                           start_word=start_word,
                           end_word=end_word,
                           score=session['advanced_score'])


@app.route('/expert_mode', methods=['GET', 'POST'])
def expert_mode():
    error_message = None
    success_message = None
    mode = "expert"

    # Initialize score and moves if not already set
    if 'expert_score' not in session:
        session['expert_score'] = 50  # Initial score for Expert Mode
    if 'expert_moves' not in session:
        session['expert_moves'] = 10  # Initial moves for Expert Mode

    # Ensure words exist and have valid paths
    if 'expert_start_word' not in session or 'expert_end_word' not in session:
        while True:
            start_word = generate_random_word(mode)
            end_word = generate_random_word(mode)
            if bfs(start_word, end_word, mode):  # Verify a valid path exists
                break
        session['expert_start_word'] = start_word
        session['expert_end_word'] = end_word
        print(f" Words generated: Start='{start_word}', End='{end_word}'")

    start_word = session['expert_start_word']
    end_word = session['expert_end_word']

    print(f" Current words in session: Start='{start_word}', End='{end_word}'")

    if request.method == 'POST':
        user_input = request.form.get('user_input').lower()

        if len(user_input) != 5:
            error_message = "Input word must be exactly 5 letters long."
            session['expert_score'] -= 20
            session['expert_moves'] -= 1
        elif not validate_word(user_input, mode):
            error_message = "Invalid word entered. Please try again."
            session['expert_score'] -= 20
            session['expert_moves'] -= 1
        else:
            changes = sum(1 for a, b in zip(start_word, user_input) if a != b)
            if changes != 1:
                error_message = "You must change exactly one letter."
                session['expert_score'] -= 20
                session['expert_moves'] -= 1
            else:
                # Valid move
                session['expert_score'] += 50
                session['expert_moves'] -= 1
                session['expert_start_word'] = user_input

                if user_input == end_word:
                    success_message = "Success! You reached the end word!"
                    session.pop('expert_start_word', None)
                    session.pop('expert_end_word', None)

        # Game over if moves run out
        if session['expert_moves'] <= 0:
            error_message = "Game Over! You ran out of moves."
            session.pop('expert_start_word', None)
            session.pop('expert_end_word', None)

        # If words were popped, generate a new valid pair
        if 'expert_start_word' not in session or 'expert_end_word' not in session:
            while True:
                start_word = generate_random_word(mode)
                end_word = generate_random_word(mode)
                if bfs(start_word, end_word, mode):
                    break
            session['expert_start_word'] = start_word
            session['expert_end_word'] = end_word
            session['expert_moves'] = 10  # Reset moves for new game
            print(f" New words generated after completion/game over: Start='{start_word}', End='{end_word}'")

    return render_template('expert.html',
                           start_word=session['expert_start_word'],
                           end_word=session['expert_end_word'],
                           success_message=success_message,
                           error_message=error_message,
                           score=session['expert_score'],
                           moves=session['expert_moves'])

@app.route('/refresh_words')
def refresh_words():
    mode = request.args.get('mode', 'beginner')
    start_word = generate_random_word(mode)
    end_word = generate_random_word(mode)
    if mode == "beginner":
        session['beginner_start_word'] = start_word
        session['beginner_end_word'] = end_word
    elif mode == "advanced":
        session['advanced_start_word'] = start_word
        session['advanced_end_word'] = end_word
    return jsonify({'start_word': start_word, 'end_word': end_word})

@app.route('/new_game')
def new_game():
    mode = request.args.get('mode', 'beginner')
    if mode == "beginner":
        session['beginner_score'] = 10
        session['beginner_start_word'] = generate_random_word(mode)
        session['beginner_end_word'] = generate_random_word(mode)
        return redirect(url_for('beginner_mode'))
    elif mode == "advanced":
        session['advanced_score'] = 10
        session['advanced_start_word'] = generate_random_word(mode)
        session['advanced_end_word'] = generate_random_word(mode)
        return redirect(url_for('advanced_mode'))
    elif mode == "expert":
        session['expert_score'] = 100
        session['expert_moves'] = 10
        session['expert_start_word'] = generate_random_word(mode)
        session['expert_end_word'] = generate_random_word(mode)
        return redirect(url_for('expert_mode'))
    return redirect(url_for('home'))

@app.route('/ai_hint/<algorithm>', methods=['GET'])
def ai_hint(algorithm):
    mode = request.args.get('mode', 'beginner')
    start_word = request.args.get('start_word')
    end_word = request.args.get('end_word')

    if not validate_word(start_word, mode) or not validate_word(end_word, mode):
        return jsonify({'error': 'Invalid start or end word'})

    if algorithm == 'UCS':
        path = ucs(start_word, end_word, mode)
    elif algorithm == 'BFS':
        path = bfs(start_word, end_word, mode)
    elif algorithm == 'A*':
        path = a_star(start_word, end_word, mode)
    else:
        return jsonify({'error': 'Invalid algorithm selected'})

    if path:
        return jsonify({'hint': path})
    else:
        return jsonify({'error': 'No valid transformation path found'})

@app.route('/generate_graph', methods=['GET'])
def generate_graph():
    mode = request.args.get('mode', 'beginner')
    if mode == "beginner":
        start_word = session.get('beginner_start_word', None)
        end_word = session.get('beginner_end_word', None)
    elif mode == "advanced":
        start_word = session.get('advanced_start_word', None)
        end_word = session.get('advanced_end_word', None)
    else:
        return jsonify({'error': 'Invalid mode'})

    algorithm = request.args.get('algorithm', 'BFS').upper()  # default BFS if not provided

    if not start_word or not end_word:
        return jsonify({'error': 'Start or end word not found in session'})

    if not validate_word(start_word, mode) or not validate_word(end_word, mode):
        return jsonify({'error': 'Invalid start or end word'})

    # 1. Compute the optimal path using the chosen algorithm
    if algorithm == 'UCS':
        optimal_path = ucs(start_word, end_word, mode)
    elif algorithm in ['A*', 'A']:
        optimal_path = a_star(start_word, end_word, mode)
    else:  # BFS by default
        optimal_path = bfs(start_word, end_word, mode)

    if not optimal_path:
        return jsonify({'error': 'No valid transformation path found'})

    # 2. Compute the set of "useful" nodes:
    # A node is useful if it is reachable from start AND the goal is reachable from it.
    from collections import deque

    def bfs_all_reachable(root):
        visited = set([root])
        q = deque([root])
        while q:
            current = q.popleft()
            for nbr in get_neighbors(current, mode):
                if nbr not in visited:
                    visited.add(nbr)
                    q.append(nbr)
        return visited

    visited_from_start = bfs_all_reachable(start_word)
    visited_from_end = bfs_all_reachable(end_word)
    useful_nodes = visited_from_start.intersection(visited_from_end)

    # 3. Optional threshold to limit graph size (adjust as needed)
    max_nodes = 50
    if len(useful_nodes) > max_nodes:
        # If too many nodes, restrict to the optimal path plus a limited neighborhood
        useful_nodes = set(optimal_path)
        q = deque(optimal_path)
        while q and len(useful_nodes) < max_nodes:
            current = q.popleft()
            for nbr in get_neighbors(current, mode):
                if nbr in visited_from_end and nbr not in useful_nodes:
                    useful_nodes.add(nbr)
                    q.append(nbr)

    # 4. Build the subgraph using only the useful nodes and edges among them
    subG = nx.Graph()
    for node in useful_nodes:
        for nbr in get_neighbors(node, mode):
            if nbr in useful_nodes:
                subG.add_edge(node, nbr)

    # 5. Determine optimal path edges for highlighting
    optimal_path_edges = set()
    for i in range(len(optimal_path) - 1):
        # For an undirected graph, add both orders
        optimal_path_edges.add((optimal_path[i], optimal_path[i+1]))
        optimal_path_edges.add((optimal_path[i+1], optimal_path[i]))

    # 6. Compute layout for subgraph with enhanced spacing:
    n_nodes = subG.number_of_nodes()
    # Dynamically adjust figure size based on node count (capped between 6 and 20 inches)
    fig_size = max(6, min(30, 0.5 * n_nodes))
    # Increase the optimal inter-node distance using k (default ~1/sqrt(n)); here we double it
    k_val = 5*(2 / (n_nodes**0.5)) if n_nodes > 0 else 0.1
    pos = nx.spring_layout(subG, k=k_val, iterations=100)

    # 7. Draw the subgraph with dynamic figure size and clear node spacing
    plt.figure(figsize=(fig_size, fig_size))

    # Separate edges into optimal vs. alternative
    all_edges = subG.edges()
    optimal_edges_list = [e for e in all_edges if e in optimal_path_edges]
    alternative_edges_list = [e for e in all_edges if e not in optimal_path_edges]

    # Color nodes: optimal path nodes in yellow, others in light blue
    node_colors = []
    for node in subG.nodes():
        if node in optimal_path:
            node_colors.append('yellow')
        else:
            node_colors.append('lightblue')

    # Draw nodes, labels, and edges with enhanced spacing
    nx.draw_networkx_nodes(subG, pos, nodelist=list(subG.nodes()),
                           node_color=node_colors, node_size=800)
    nx.draw_networkx_labels(subG, pos, font_size=10, font_color='black')
    nx.draw_networkx_edges(subG, pos, edgelist=optimal_edges_list,
                           edge_color='red', width=3)
    nx.draw_networkx_edges(subG, pos, edgelist=alternative_edges_list,
                           edge_color='gray', width=1)

    plt.axis('off')
    plt.tight_layout()

    # 8. Save plot to a bytes buffer, encode to base64, and return in JSON
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return jsonify({'graph_url': f"data:image/png;base64,{graph_url}"})

import os
import time
import string
import json
import errno
import numpy as np
import tensorflow as tf
from agent import Agent
import matplotlib.pyplot as plt
import sys
import math


FIFO_SUPPRESSION_VALUE = 'fifo_suppression_value'
FIFO_OBJECT_DETAILS = 'fifo_object_details'
EMBEDDING_DIMENSION = 80
EVALUATION_INTERVAL = 100  # Evaluate every 1000 steps
PERFORMANCE_THRESHOLD = 5.5 # Threshold for performance to resume training
experience_dict = {}
reward_history = []
score = 0

def generate_positional_embedding(text):
    alphabet = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*()_-+={}[]|\:;'<>?,./\""
    vocab = alphabet + digits + symbols
    embedding = []
    for idx, char in enumerate(text.lower()):
        if char in vocab:
            char_idx = vocab.index(char)
            embedding.append(char_idx)
    while len(embedding) < EMBEDDING_DIMENSION:
        embedding.append(0)
    embedding = embedding[:EMBEDDING_DIMENSION]
    return embedding

def read_state():
    with open(FIFO_OBJECT_DETAILS, 'r') as read_pipe:
        states_string = read_pipe.read()
    if not states_string:
        raise ValueError("No data received from FIFO")
    return json.loads(states_string)

def write_action(action):
    with open(FIFO_OBJECT_DETAILS, 'w') as write_pipe:
        write_pipe.write(f"{action}")

def calculate_reward(states_dict, previous_dc):
    dc = float(states_dict["ewma_dc"])
    is_forwarded = states_dict["wasForwarded"] == "true"
    suppression_time = float(states_dict["suppression_time"].split(" ")[0])
    forwarded_status = 0 if is_forwarded else 2
    dc_diff = 0
    if dc == previous_dc == 1:
        dc_diff = 5
    elif dc == previous_dc:
        dc_diff = -int(dc)
    elif dc > previous_dc:
        dc_diff = 2 * (previous_dc - int(dc))
    else:
        dc_diff = previous_dc - int(dc)
    if suppression_time > 0:
        reward = forwarded_status + dc_diff - math.log10(suppression_time)
    else:
        reward = forwarded_status + dc_diff
    return reward, dc

def evaluate_performance(reward_history, interval):
    recent_rewards = reward_history[-interval:]
    average_reward = np.mean(recent_rewards)
    return average_reward

def main(node_name):
    try:
        os.mkfifo(FIFO_OBJECT_DETAILS, mode=0o777)
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            raise
    agent = Agent(node_name)
    counter = 1
    previous_dc = 1
    score = 0
    training = True
    # training = False
    model_dir = "/home/bidhya/workspace/STRL/rl/modelmultiplewithoutsuppressionreward"
    node_dir = os.path.join(model_dir, node_name)

    while True:
        try:
            start_time = time.time()
            # Read and process state
            states_dict = read_state()
            result = '/'.join(str(value) for value in states_dict.values()).split(" ")[0]
            prefix_name_with_packet = f"{states_dict['name']}/{states_dict['type']}"
            embeddings = generate_positional_embedding(result)
            new_embeddings = tf.convert_to_tensor([embeddings], dtype=tf.float32)
            # Select action
            action = int(agent.choose_action(new_embeddings))
            write_action(action)
            print("State with action", states_dict, action)
            # Calculate reward and update agent if training
            
            if prefix_name_with_packet in experience_dict:
                reward, previous_dc = calculate_reward(states_dict, previous_dc)
                    # score += reward
                done = 0
                previous_state = experience_dict[prefix_name_with_packet]
                current_state = new_embeddings
                if training:
                    print("Agent is learning")
                    agent.learn(previous_state, reward, current_state, done)
                reward_history.append(reward)
                print("State with action", states_dict, action, "Reward", reward)

            # Update experience
            experience_dict[prefix_name_with_packet] = new_embeddings
            

            if counter == 1:
                print("Counter 1: ", node_dir, os.path.exists(node_dir))               
                if os.path.exists(node_dir):
                    agent.load_models()

            # Evaluation phase
            # if node_name == "sta4":
            #     PERFORMANCE_THRESHOLD = 4.8
            if counter % EVALUATION_INTERVAL == 0:
                average_reward = evaluate_performance(reward_history, EVALUATION_INTERVAL)
                print(f"Evaluation at step {counter}: Average Reward = {average_reward}")
                if average_reward >= PERFORMANCE_THRESHOLD:
                    print("Pausing training due to satisfactory performance.")
                    # agent.save_models()
                    training = False
                else:
                    print("Resuming training due to poor performance.")
                    # if os.path.exists(node_dir):
                    #     agent.load_models()  # Load the model when resuming training
                    training = False
            
            end_time = time.time()
            print("Execution period", (end_time - start_time) * 1000, "Counter", counter, " training ", training)
            counter += 1
        except Exception as e:
            print("Exception:", e)

if __name__ == "__main__":
    arg1 = sys.argv[1]

    print(f"Argument 1: {arg1}")
    main(arg1)

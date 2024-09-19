import cProfile
import pstats
import io

pr = cProfile.Profile()
pr.enable()




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
from datetime import datetime

def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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

def get_embedding_of_prefix(prefix):
    positional_embedding = generate_positional_embedding(prefix)
    return tf.convert_to_tensor([positional_embedding], dtype=tf.float32)

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
    start_mkfifo = time.time()
    try:
        os.mkfifo(FIFO_OBJECT_DETAILS, mode=0o777)
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            raise
    end_mkfifo = time.time()
    print(f"{get_timestamp()} Execution time for mkfifo ",(end_mkfifo-start_mkfifo)*1000)
    start_time_agent_instance = time.time()
    agent = Agent(node_name)
    end_time_agent_instance = time.time()
    print(f"{get_timestamp()}Execution time for agent instance creation ",( end_time_agent_instance - start_time_agent_instance)*1000)
    start_time_load_model = time.time()
    agent.load_models() # load models from checkpoint
    end_time_load_model = time.time()
    print(f"{get_timestamp()}Execution time for Loading model time ", (end_time_load_model - start_time_load_model)*1000)
    counter = 1
    previous_dc = 1 # previous duplicate count
    training = False # True
    fifo_read_time = 0
    fifo_write_time = 0
    embedding_time = 0
    reward_time = 0
    choosing_action_time = 0
    training_time = 0
    execution_time = 0
    
    while True:
        try:
            start_time = time.time()
            print("The start time for all the process ", start_time)
            # Read and process state
            start_time_read_state = time.time()
            states_dict = read_state() # {name : , type: , ewma_dc: , is_forwarded: , supression_time: }  
            end_time_read_state = time.time()
            fifo_read_time = (end_time_read_state - start_time_read_state)*1000 
            print(f"{get_timestamp()}Execution time for Read state time ", fifo_read_time, " start time was ", start_time_read_state)
    
            result = '/'.join(str(value) for value in states_dict.values()).split(" ")[0]
            prefix_name_with_packet = f"{states_dict['name']}/{states_dict['type']}"      
            start_time_embedding = time.time()
            new_embeddings = get_embedding_of_prefix(result)
            end_time_embedding = time.time()
            embedding_time = (end_time_embedding - start_time_embedding) * 1000
            # Select action
            start_time_choose_action = time.time()
            action = int(agent.choose_action(new_embeddings))
            end_time_choose_action = time.time()
            choosing_action_time = (end_time_choose_action - start_time_choose_action) *1000
            start_time_write_action = time.time()
            write_action(action)
            end_time_write_action = time.time()
            fifo_write_time = (end_time_write_action - start_time_write_action)*1000
            print(f"{get_timestamp()}Execution time for Write action time ", (end_time_write_action - start_time_write_action)*1000)
            print(f"{get_timestamp()}State with action", states_dict, action)
            st = float(states_dict["suppression_time"].split(" ")[0])
            # Calculate reward and update agent if training
            start_time_dict = time.time()
            if prefix_name_with_packet in experience_dict:
                start_time_calculate_reward = time.time()
                reward, previous_dc = calculate_reward(states_dict, previous_dc)
                end_time_calculate_reward = time.time()
                reward_time = (end_time_calculate_reward - start_time_calculate_reward)*1000
                print(f"{get_timestamp()}Execution time for Calculating reward time ", reward_time, " Embedding start time", start_time_calculate_reward)
                
                    # score += reward
                done = 0
                previous_state = experience_dict[prefix_name_with_packet]
                current_state = new_embeddings
                if training:
                    print(f"{get_timestamp()}Agent is learning")
                    start_learn = time.time()
                    agent.learn(previous_state, reward, current_state, done)
                    end_learn = time.time()
                    training_time = (end_learn - start_learn) * 1000    
                reward_history.append(reward)
                print(f"{get_timestamp()}State with action", states_dict, action, "Reward", reward)
            end_time_dict = time.time()
            print(f"{get_timestamp()}Execution time for dictionary search ", (end_time_dict - start_time_dict)*1000)
            # Update experience
            experience_dict[prefix_name_with_packet] = new_embeddings
            

            # if counter == 1:
            #     print("Counter 1: ", node_dir, os.path.exists(node_dir))               
            #     if os.path.exists(node_dir):
            #         agent.load_models()

            # Evaluation phase
            # if node_name == "sta4":
            #     PERFORMANCE_THRESHOLD = 4.8
            # if counter % EVALUATION_INTERVAL == 0:
            #     average_reward = evaluate_performance(reward_history, EVALUATION_INTERVAL)
            #     print(f"Evaluation at step {counter}: Average Reward = {average_reward}")
            #     if average_reward >= PERFORMANCE_THRESHOLD:
            #         print("Pausing training due to satisfactory performance.")
            #         # agent.save_models()
            #         training = False
            #     else:
            #         print("Resuming training due to poor performance.")
            #         # if os.path.exists(node_dir):
            #         #     agent.load_models()  # Load the model when resuming training
            #         training = False
            
            end_time = time.time()
            execution_time = (end_time - start_time)*1000
            print("Analysis Counter: ", counter, " Node: ", node_name, "Read time: ", fifo_read_time, " Write time: ", fifo_write_time, " Embedding time: ", embedding_time, " Choose action: ", choosing_action_time, " Reward calculate: ", reward_time, " Execution time: ", execution_time, "Suppression time: ", st, " Training time: ", training_time)

            counter = counter + 1
           

        except Exception as e:
            print(f"{get_timestamp()}Exception:", e)

if __name__ == "__main__":
    arg1 = sys.argv[1]

    print(f"Argument 1: {arg1}")
    main(arg1)





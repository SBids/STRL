import tensorflow as tf
from tensorflow.keras.optimizers import Adam
import tensorflow_probability as tfp
from network import ActorCriticNetwork
import os
import tensorflow.keras as keras
import datetime
import wandb

chkpt_dir_path = "/home/bidhya/workspace/STRLprac/rl/model_aug30_1045"
# chkpt_dir_path = "/home/bidhya/workspace/STRLprac/rl/newmodel"

class Agent:
    def __init__(self, node_name, gamma=0.99, n_actions=1, chkpt_dir=chkpt_dir_path):
        self.gamma = gamma
        self.n_actions = n_actions
        self.node_name = node_name
        self.actor_critic = ActorCriticNetwork(n_actions=n_actions)
        self.actor_critic.compile(optimizer=Adam(learning_rate=0.0003), metrics=['accuracy'])
        wandb.login(key='540b361048b814fe60c9e37f79b5598c5588268e')
        wandb.init(
            # set the wandb project where this run will be logged
            project="ac-rl",

            # track hyperparameters and run metadata
            config={
            "learning_rate": 0.0003
            }
        )
        
        # Create directory for this node if it doesn't exist
        self.chkpt_dir_node = os.path.join(chkpt_dir, node_name)
        os.makedirs(self.chkpt_dir_node, exist_ok=True)
        
        self.checkpoint_file = os.path.join(self.chkpt_dir_node, '_actor_critic_')

    def choose_action(self, observation):
        _, mu, sigma = self.actor_critic(observation)
        print("Mean is ", mu, " and sigma is ", sigma)
        action_distribution = tfp.distributions.Normal(loc=mu, scale=sigma)
        raw_action = action_distribution.sample(seed=42)
        print("raw_action ", raw_action, " mu ", mu, " sigma ", sigma)
        action = tf.clip_by_value(raw_action, clip_value_min=15.0, clip_value_max=4000.00)
        log_prob = action_distribution.log_prob(action)
        self.action = action
        action = action[0]
        return action.numpy()[0]

    def get_reward(self, ewma_duplicate_count, rtt, srtt, alpha=0.5, beta=0.4, gamma=0.3):
        if rtt is not None:
            reward = -(alpha * float(ewma_duplicate_count) + beta * rtt + gamma * (rtt - srtt))
        else:
            reward = -(alpha * float(ewma_duplicate_count) + gamma * srtt)
        return reward

    def learn(self, state, reward, state_, done):
        state = tf.convert_to_tensor([state], dtype=tf.float32)
        reward = tf.convert_to_tensor([reward], dtype=tf.float32)    
        done = tf.convert_to_tensor([int(done)], dtype=tf.float32)    

        with tf.GradientTape() as tape:
            value, mu, sigma = self.actor_critic(state)
            print("Value from critic ", value)
            print("mean mu from actor head ", mu, " for state ", state)
            print("sigma standard deviation from actor head ", sigma)
            value_, _, _ = self.actor_critic(state_)
            td_error = reward + self.gamma * value_ * (1 - done) - value
            print("TD error which is feedback to actor ", td_error)
            advantage = td_error
            dist = tfp.distributions.Normal(loc=mu, scale=sigma)
            log_prob = dist.log_prob(self.action)
            actor_loss = -log_prob * tf.stop_gradient(advantage)
            critic_loss = tf.square(td_error)
            loss = actor_loss + critic_loss

            wandb.log({"actor_loss": actor_loss, "critic_loss": critic_loss, "loss": loss, "td_error": td_error})

            print("Total Loss", loss)
        
        gradients = tape.gradient(loss, self.actor_critic.trainable_variables)
        self.actor_critic.optimizer.apply_gradients(zip(gradients, self.actor_critic.trainable_variables))




    def save_models(self):
        print("Saving model to =======================", self.checkpoint_file)
        # Print the model weights before saving
        for layer in self.actor_critic.layers:
            print(f"Layer: {layer.name}")
            weights = layer.get_weights()
            for weight in weights:
                print("Weights", weight)
        self.actor_critic.save_weights(self.checkpoint_file)

    def load_models(self):
        if os.path.isdir(self.chkpt_dir_node):
            print("Loading model from", self.checkpoint_file)
            self.actor_critic.load_weights(self.checkpoint_file)
            
        else:
            print("No checkpoint found at", self.checkpoint_file)

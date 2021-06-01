import os
import numpy as np

import tensorflow as tf
from tensorflow.keras.layers import Input, Dense, Dropout, Flatten, Embedding, multiply
from tensorflow.keras import Model

from tensorflow.keras.optimizers import Adam

class CGAN():

    def __init__(self, gan_args):
        [self.batch_size, lr, self.noise_dim,
         self.data_dim, num_classes, self.classes, layers_dim] = gan_args

        self.generator = Generator(self.batch_size, num_classes). \
            build_model(input_shape=(self.noise_dim,), dim=layers_dim, data_dim=self.data_dim)

        self.discriminator = Discriminator(self.batch_size, num_classes). \
            build_model(input_shape=(self.data_dim,), dim=layers_dim)

        optimizer = Adam(lr, 0.5)
        self.discriminator.trainable = True
        # Build and compile the discriminator
        self.discriminator.compile(loss='binary_crossentropy',
                                   optimizer=optimizer,
                                   metrics=['accuracy'])

        # The generator takes noise as input and generates imgs
        z = Input(shape=(self.noise_dim,), batch_size=self.batch_size)
        label = Input(shape=(1,), batch_size=self.batch_size)
        record = self.generator([z, label])

        # For the combined model we will only train the generator
        self.discriminator.trainable = False

        # The discriminator takes generated images as input and determines validity
        validity = self.discriminator([record, label])

        # The combined model  (stacked generator and discriminator)
        # Trains the generator to fool the discriminator
      
        self.combined = Model([z, label], validity)
        self.combined.compile(loss='binary_crossentropy', optimizer=optimizer)

    def get_data_batch(self, train, batch_size, seed=0):
        # # random sampling - some samples will have excessively low or high sampling, but easy to implement
        # np.random.seed(seed)
        # x = train.loc[ np.random.choice(train.index, batch_size) ].values
        # iterate through shuffled indices, so every sample gets covered evenly

        start_i = (batch_size * seed) % len(train)
        stop_i = start_i + batch_size
        shuffle_seed = (batch_size * seed) // len(train)
        np.random.seed(shuffle_seed)
        train_ix = np.random.choice(list(train.index), replace=False, size=len(train))  # wasteful to shuffle every time
        train_ix = list(train_ix) + list(train_ix)  # duplicate to cover ranges past the end of the set
        x = train.loc[train_ix[start_i: stop_i]].values
        return np.reshape(x, (batch_size, -1))

    def train(self, data, train_arguments):
        [cache_prefix, label_dim, epochs, sample_interval, data_dir] = train_arguments

        # Adversarial ground truths
        valid = np.ones((self.batch_size, 1))
        fake = np.zeros((self.batch_size, 1))

        for epoch in range(epochs):
            self.discriminator.trainable = True
            # ---------------------
            #  Train Discriminator
            # ---------------------
            batch_y = self.get_data_batch(data, self.batch_size)
            label = batch_y[:, label_dim]
            batch_x = batch_y[:, :-1]
            noise = tf.random.normal((self.batch_size, self.noise_dim))

            # Generate a batch of new records
            gen_records = self.generator.predict([noise, label])
            
            # Train the discriminator
            d_loss_real = self.discriminator.train_on_batch([batch_x, label], valid)
            d_loss_fake = self.discriminator.train_on_batch([gen_records, label], fake)
            d_loss = 0.5 * np.add(d_loss_real, d_loss_fake)

            # ---------------------
            #  Train Generator
            # ---------------------
            self.discriminator.trainable = False
            noise = tf.random.normal((self.batch_size, self.noise_dim))
            # Train the generator (to have the discriminator label samples as valid)
            g_loss = self.combined.train_on_batch([noise, label], valid)

            # Plot the progress
            print("%d [D loss: %f, acc.: %.2f%%] [G loss: %f]" % (epoch, d_loss[0], 100 * d_loss[1], g_loss))

            # If at save interval => save generated image samples
            if epoch % sample_interval == 0:
                # Test here data generation step
                # save model checkpoints
                model_checkpoint_base_name = data_dir + cache_prefix + '_{}_model_weights_step_{}.h5'
                self.generator.save_weights(model_checkpoint_base_name.format('generator', epoch))
                self.discriminator.save_weights(model_checkpoint_base_name.format('discriminator', epoch))

                #Here is generating synthetic data
                z = tf.random.normal((432, self.noise_dim))
                #label_z = tf.random.uniform((432,), minval=min(self.classes), maxval=max(self.classes)+1, dtype=tf.dtypes.int32)
                #gen_data = self.generator([z, label_z])
                print('generated_data')

    def save(self, path, name):
        assert os.path.isdir(path) == True, \
            "Please provide a valid path. Path must be a directory."
        model_path = os.path.join(path, name)
        self.generator.save_weights(model_path)  # Load the generator
        return

    def load(self, path):
        assert os.path.isdir(path) == True, \
            "Please provide a valid path. Path must be a directory."
        self.generator = Generator(self.batch_size)
        self.generator = self.generator.load_weights(path)
        return self.generator

class Generator():
    def __init__(self, batch_size, num_classes):
        self.batch_size = batch_size
        self.num_classes = num_classes

    def build_model(self, input_shape, dim, data_dim):
        noise = Input(shape=input_shape, batch_size=self.batch_size)
        label = Input(shape=(1,), batch_size=self.batch_size, dtype='float32')
        label_embedding = Flatten()(Embedding(self.num_classes, 1)(label))
        input = tf.concat(axis = 1, values = [noise,label])

        x = Dense(dim, activation='relu')(input)
        x = Dense(dim * 2, activation='relu')(x)
        x = Dense(dim * 4, activation='relu')(x)
        x = Dense(data_dim)(x)
        return Model(inputs=[noise, label], outputs=x)

class Discriminator():
    def __init__(self, batch_size, num_classes):
        self.batch_size = batch_size
        self.num_classes = num_classes

    def build_model(self, input_shape, dim):
        events = Input(shape=input_shape, batch_size=self.batch_size)
        label = Input(shape=(1,), batch_size=self.batch_size, dtype='float32')
        label_embedding = Flatten()(Embedding(self.num_classes, 1)(label))
        events_flat = Flatten()(events)
        input = tf.concat(axis = 1, values = [events,label])

        x = Dense(dim * 4, activation='relu')(input)
        x = Dropout(0.1)(x)
        x = Dense(dim * 2, activation='relu')(x)
        x = Dropout(0.1)(x)
        x = Dense(dim, activation='relu')(x)
        x = Dense(1, activation='sigmoid')(x)
        return Model(inputs=[events, label], outputs=x)






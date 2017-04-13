from keras.layers import Input, Dense, Reshape, Flatten, Dropout
from keras.models import Model, Sequential, load_model
from keras import optimizers
from sklearn.base import TransformerMixin
from keras import regularizers
import numpy as np
from keras import backend as K
import operator


class ContextDeepAutoEncoder(TransformerMixin):
    def __init__(self, input_shape=(25, 128), dims = (256, 128, 64, 128, 256), output_shape=(25, 128), activation_sparsity=0.01,
                 template_sparsity=1, num_decoders = 2, loss='mean_squared_error', optimizer='adadelta', dropout = True):
        if loss == 'mask_loss':
            loss = self.mask_loss
        self.loss = loss
        self.optimizer = optimizer

        self.input_frame = Input(shape=input_shape)
        encoder = Sequential()

        #encoding

        #noise_layer = GaussianNoise(.1, input_shape=(input_shape,))
        #network.add(noise_layer)
        even = 1
        if len(dims) % 2 == 0:
            even = 0

        encoder.add(Flatten(input_shape=input_shape))
        # vertical_bias = Dense(50, kernel_initializer='zeros', use_bias=False)
        for i in range((len(dims) / 2) + even):
            encoder.add(Dense(dims[i], activation='relu'))
            if dropout:
                encoder.add(Dropout(.8))


        #decoding
        def create_decoder_for_source(decoder):
            decoder.add(Dense(dims[len(dims) / 2 + even], activation='relu',
                input_shape=(dims[len(dims) / 2],)))
            for i in range((len(dims) / 2) + even, len(dims)):
                decoder.add(Dense(dims[i], activation='relu'))
                if dropout:
                    encoder.add(Dropout(.8))
            decoder.add(Dense(reduce(operator.mul, list(output_shape)), activation='relu'))
            if dropout:
                encoder.add(Dropout(.8))
            decoder.add(Reshape(output_shape))
            return decoder

        #one decoder per output source
        self.decoders = []
        for num_decoder in range(num_decoders):
            self.decoders.append(create_decoder_for_source(Sequential()))

        #connect the encoder and decoder modules to the input
        encoder = encoder(self.input_frame)
        self.decoders = [decoder(encoder) for decoder in self.decoders]
        self.autoencoder = Model(inputs=[self.input_frame], outputs=self.decoders)
        self.has_fit_been_run = False
        self.autoencoder.compile(loss=self.loss, optimizer=self.optimizer)

    def mask_loss(self, y_true, y_pred):
        all_sources = K.sum(self.decoders)
        interfering_source_mask = (all_sources - y_pred) > (all_sources + K.epsilon())
        mask = y_pred > (all_sources + K.epsilon())
        diff = K.mean(K.square(interfering_source_mask - mask))
        y_mask = mask * self.input_frame
        return K.mean(K.square(y_true - y_mask)) - self.alpha*diff

    def fit(self, input_data, output_data, **kwargs):
        self.autoencoder.fit(input_data, output_data,
                             **kwargs)
        self.has_fit_been_run = True
        return self

    def fit_generator(self, *args, **kwargs):
        self.autoencoder.fit_generator(*args, **kwargs)
        self.has_fit_been_run = True
        return self

    def transform(self, X):
        raise NotImplementedError("Haven't fgured out this function yet!")

        # if not self.has_fit_been_run:
        #     raise ValueError("Model has not been fit! Run fit() before calling this.")
        # self.representation = self.encoder.predict(X)
        # return self.representation

    def reconstruction_error(self, X):
        if not self.has_fit_been_run:
            raise ValueError("Model has not been fit! Run fit() before calling this.")
        reconstruction = self.autoencoder.predict(X)
        loss = self.error_measure(X, reconstruction[0]) - self.error_measure(X, reconstruction[1])
        return loss

    def reconstruction_error_by_frame(self, X):
        if not self.has_fit_been_run:
            raise ValueError("Model has not been fit! Run fit() before calling this.")

        loss = self.error_measure(X, self.autoencoder.predict(X), axis = 0)
        return loss

    def inverse_transform(self, X):
        if not self.has_fit_been_run:
            raise ValueError("Model has not been fit! Run fit() before calling this.")
        reconstruction = self.autoencoder.predict(X)
        return reconstruction

    def save(self, path):
        self.autoencoder.save(path)

    def load(self, path):
        self.autoencoder = load_model(path, custom_objects={'mask_loss': self.mask_loss})
        self.has_fit_been_run = True
        return self

    def error_measure(self, y_true, y_pred, axis = None):
        # y_true = y_true.astype(dtype=np.float64)
        # y_pred = y_pred.astype(dtype=np.float64)
        # return K.eval(K.sum(y_true * (K.log(y_true + K.epsilon()) - K.log(y_pred + K.epsilon())) - y_true + y_pred))
        # return np.sum(np.multiply(y_true, (np.log(y_true + K.epsilon()) - np.log(y_pred + K.epsilon())))
        #               - y_true + y_pred, axis=axis) \
        #        / float(y_true.shape[0])
        return np.mean(np.square(y_true - y_pred))

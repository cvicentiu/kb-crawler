<template>
  <div class="container mt-5">
    <h2 class="text-center mb-4">MariaDB KB Expert Demo</h2>
    <div class="d-flex flex-row gap-3">
      <div class="border rounded mb-4 flex-grow-1 p-3" style="width: 50%">No context bot</div>
      <div class="border rounded mb-4 flex-grow-1 p-3" style="width: 50%">Context aware bot</div>
    </div>
    <div class="d-flex flex-row gap-3">
      <!-- Chat Display -->
      <div class="chat-box border rounded p-3 mb-4 flex-grow-1" style="width: 50%; height: 400px; overflow-y: scroll;">
        <div v-for="(message, index) in messages" :key="index" class="my-2">
          <div :class="message.sender === 'user' ? 'text-end' : 'text-start'">
            <b>{{ message.sender === 'user' ? 'You' : 'Bot' }}: </b>
            <p class="d-inline"><span v-html="message.text"></span></p>
          </div>
        </div>
      </div>
      <!-- Chat Display -->
      <div class="chat-box border rounded p-3 mb-4 flex-grow-1" style="width: 50%; height: 400px; overflow-y: scroll;">
        <div v-for="(message, index) in messagesSmart" :key="index" class="my-2">
          <div :class="message.sender === 'user' ? 'text-end' : 'text-start'">
            <b>{{ message.sender === 'user' ? 'You' : 'Bot' }}: </b>
            <p class="d-inline"><span v-html="message.text"></span></p>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Form -->
    <form @submit.prevent="handleSubmit">
      <div class="input-group">
        <input 
          type="text" 
          class="form-control" 
          placeholder="Type your message..." 
          v-model="userInput"
          required
        />
        <button class="btn btn-primary" type="submit" :disabled="loading">
          {{ loading ? "Sending..." : "Send" }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.chat-box {
  background-color: #f8f9fa;
}
</style>


<script>
import axios from 'axios';

export default {
  data() {
    return {
      userInput: '',
      messages: [],
      messagesSmart: [],
      loading: false,
    };
  },
  methods: {
    async handleSubmit() {
      if (!this.userInput.trim()) return;

      // Add user message to messages
      this.messages.push({ sender: 'user', text: this.userInput });
      // Add user message to messages
      this.messagesSmart.push({ sender: 'user', text: this.userInput });

      // Store input and clear input box
      const prompt = this.userInput;
      this.userInput = '';
      this.loading = true;

      try {
        // Make API call to your backend to get ChatGPT response
        const fetchAxios = axios.create({
          adapter: 'fetch'
        });
        const response = await fetchAxios.post(
          'http://localhost/api/ask-bot/',
          { prompt },
          { responseType: 'stream'},
        );
        const responseSmart = await fetchAxios.post(
          'http://localhost/api/ask-bot-smart/',
          { prompt },
          { responseType: 'stream'},
        );

        const readerDumb = response.data.getReader();
        const readerSmart = responseSmart.data.getReader();

        async function readStream(prefix, reader, messages) {
          const decoder = new TextDecoder();  // To decode the stream into text
          let result = prefix;

          while (true) {
            const { done, value } = await reader.read();
            const chunkText = decoder.decode(value, { stream: true });


            if (done) {
              console.log("Stream finished.");
              break;
            }

            const lines = chunkText;
            for (let line of lines) {
              result += line;
              messages[messages.length - 1].text += line;
            }
          }


          return result;
        };

        // Add ChatGPT response to messages
        this.messages.push({ sender: 'bot', text: '' });
        this.messagesSmart.push({ sender: 'bot', text: '' });
        const [resultOne, resultTwo] = await Promise.all(
          [readStream('D', readerDumb, this.messages),
           readStream('S', readerSmart, this.messagesSmart)]);
      } catch (error) {
        console.error('Error fetching reply:', error);
        this.messages.push({ sender: 'bot', text: "Sorry, I couldn't fetch a response. Please try again." });
        this.messagesSmart.push({ sender: 'bot', text: "Sorry, I couldn't fetch a response. Please try again." });
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>


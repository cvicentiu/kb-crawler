<template>
  <div class="container mt-5">
    <h2 class="text-center mb-4">MariaDB KB Expert Demo</h2>
    <!-- Chat Display -->
    <div class="chat-box border rounded p-3 mb-4" style="height: 400px; overflow-y: scroll;">
      <div v-for="(message, index) in messages" :key="index" class="my-2">
        <div :class="message.sender === 'user' ? 'text-end' : 'text-start'">
          <b>{{ message.sender === 'user' ? 'You' : 'Bot' }}: </b>
          <p class="d-inline"><span v-html="message.text"></span></p>
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
      loading: false,
    };
  },
  methods: {
    fetchChatGPTResponse(prompt) {
      // Start receiving streamed events from the Django server
      this.eventSource = new EventSource(`http://localhost/api/ask-bot/`);
      let chatGPTMessage = { sender: 'chatgpt', text: '' };
      this.messages.push(chatGPTMessage);

      this.eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          this.loading = false;
          this.eventSource.close();
          return;
        }

        chatGPTMessage.text += event.data;
      };

      this.eventSource.onerror = (error) => {
        console.error("Error with EventSource:", error);
        this.messages.push({ sender: 'chatgpt', text: "Error receiving response. Please try again." });
        this.loading = false;
        this.eventSource.close();
      };
    },

    async handleSubmit() {
      if (!this.userInput.trim()) return;

      // Add user message to messages
      this.messages.push({ sender: 'user', text: this.userInput });

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

        const reader = response.data.getReader();

        async function readStream(messages) {
          const decoder = new TextDecoder();  // To decode the stream into text
          let result = '';

          while (true) {
            const { done, value } = await reader.read();
            const chunkText = decoder.decode(value, { stream: true });


            if (done) {
              console.log("Stream finished.");
              break;
            }

            console.log(chunkText);
            const lines = chunkText.split('\n');
            for (let line of lines) {
              result += line;
              messages[messages.length - 1].text += line;
            }


            // Decode the chunk and add it to the result
            //result += decoded_value;
          }


          return result;
        };

        // Add ChatGPT response to messages
        this.messages.push({ sender: 'bot', text: '' });
        await readStream(this.messages);
      } catch (error) {
        console.error('Error fetching reply:', error);
        this.messages.push({ sender: 'bot', text: "Sorry, I couldn't fetch a response. Please try again." });
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>


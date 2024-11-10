// main.js/ts
import {createApp} from 'vue'
import {createBootstrap} from 'bootstrap-vue-next'

// Add the necessary CSS
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue-next/dist/bootstrap-vue-next.css'

import ChatApp from './components/ChatApp.vue'

const app = createApp(ChatApp)
app.use(createBootstrap()) // Important
app.mount('#app')

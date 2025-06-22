import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    Authorization: 'mysecretkey123'
  }
});

export default api;

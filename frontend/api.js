import axios from "axios";

const API = axios.create({
  baseURL: "/api",
  withCredentials: true        // send session cookie
});

export default API;


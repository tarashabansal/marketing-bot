import React, { useState } from "react";
import Login from "./components/login";
import Signup from "./components/signup";
import MainPage from "./components/MainPage";
import "./index.css";

export default function App() {
  const [page, setPage] = useState("login");

  const handleLogin = (data) => {
    console.log("Login:", data);
  };
  const handleSignup = (data) => {
    console.log("Signup:", data);
  };
  return <MainPage />;
  // return (
  //   <>
  //     {page === "login" ? (
  //       <Login onLogin={handleLogin} goToSignup={() => setPage("signup")} />
  //     ) : (
  //       <Signup onSignup={handleSignup} goToLogin={() => setPage("login")} />
  //     )}
  //   </>
  // );
}

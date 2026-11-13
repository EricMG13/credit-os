import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { readLibraryData } from "./data";
import "./index.css";

const container = document.getElementById("root");
if (container === null) throw new Error("index.html has no #root element");

createRoot(container).render(
  <StrictMode>
    <App result={readLibraryData(window.CREDIT_OS_DATA)} />
  </StrictMode>,
);

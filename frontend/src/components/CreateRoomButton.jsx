import "../index.css";
import React from "react";

export default function CreateRoomButton(props) {
  // Redirect to random room when user clicks button
  function handleClick() {
    if (!props.socket) {
      return;
    }
    console.log("Create Room Button Clicked");
    props.socket.send({
      type: "create_room",
    });
  }

  return (
    <div className="createRoomButton">
      <button
        type="button"
        onClick={handleClick}
        className="button"
        disabled={!props.socket}
      >
        Create a Room!
      </button>
    </div>
  );
}

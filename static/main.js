document.querySelectorAll(".like-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const postId = button.getAttribute("data-post-id");

    fetch(`/user/${currentUsername}/feed/like`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ post_id: postId }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.liked) {
          document.getElementById(`like-count-${postId}`).innerText =
            data.likes;
          button.innerText = "❤️";
        } else if (data.error) {
          alert(data.error);
        } else {
          document.getElementById(`like-count-${postId}`).innerText =
            data.likes;
          button.innerText = "🤍";
        }
      })
      .catch((error) => {
        console.error("Fehler beim Liken:", error);
      });

    anime({
      targets: button,
      scaleX: [0.2, 1.2, 1],
      scaleY: [0.2, 1.2, 1],
      duration: 500,
      easing: "easeInOutQuad",
    });
  });
});

// FOLLOW BUTTONS
document.querySelectorAll(".follow-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const id_to_follow = button.getAttribute("data-post-id");

    fetch(`/user/${username_to_follow}/follow`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id_to_follow }),
    })
      .then((response) => response.json())
      .then((data) => {
        const followButtons = document.getElementsByClassName(
          "follow-button-container",
        );

        const followBtns = document.getElementsByClassName("follow-btn");

        if (data.followed) {
          document.getElementById(`follower-count-${id_to_follow}`).innerText =
            "Follower: " + data.follower;

          button.innerText = "Gefolgt";

          anime({
            targets: followButtons,
            scaleX: [0.2, 1.2, 1],
            scaleY: [0.2, 1.2, 1],
            backgroundColor: ["#ff0000", "#ffffff"],
            duration: 500,
            easing: "easeInOutQuad",
          });

          anime({
            targets: followBtns,
            color: ["#ffffff", "#ff0000"],
            duration: 500,
            easing: "easeInOutQuad",
          });
        } else {
          document.getElementById(`follower-count-${id_to_follow}`).innerText =
            "Follower: " + data.follower;

          button.innerText = "Folgen";

          anime({
            targets: followButtons,
            scaleX: [0.2, 1.2, 1],
            scaleY: [0.2, 1.2, 1],
            backgroundColor: ["#ffffff", "#ff0000"],
            duration: 500,
            easing: "easeInOutQuad",
          });

          anime({
            targets: followBtns,
            color: ["#ff0000", "#ffffff"],
            duration: 500,
            easing: "easeInOutQuad",
          });
        }
      })
      .catch((error) => {
        console.error("Fehler beim Follow:", error);
      });
  });
});

// SEARCH BAR TOGGLE
const button = document.getElementById("search-user");
const buttonSearch = document.querySelector(".search");
const inputField = document.querySelector(".search-user-input");
const durationSearchBar = 200;

button.addEventListener("click", () => {
  if (inputField.classList.contains("open")) {
    anime.set(inputField, { transformOrigin: "left bottom" });

    anime({
      targets: [inputField, buttonSearch],
      duration: durationSearchBar,
      translateY: ["0", "200%"],
      translateX: "-50%",
      scaleX: ["1", "0.5"],
      scaleY: ["1", "0.05"],
      easing: "easeOutExpo",
      complete: () => {
        inputField.classList.remove("open");
        buttonSearch.classList.remove("open");
      },
    });
  } else {
    inputField.classList.add("open");
    buttonSearch.classList.add("open");

    anime.set(inputField, { transformOrigin: "left bottom" });

    anime({
      targets: [inputField, buttonSearch],
      translateY: ["200%", "0"],
      translateX: ["-50%", "-50%"],
      scaleX: ["0.5", "1"],
      scaleY: ["0.05", "1"],
      duration: durationSearchBar,
      easing: "easeInExpo",
    });
  }
});

// COMMENTS BUTTON
document.querySelectorAll(".comments-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const commentSection = document.getElementById("comment-section");

    if (commentSection.classList.contains("open")) {
      const feedContainer = document.getElementById("feed-window");
      const bodyWithoutTitle = document.getElementById("body-without-title");

      commentSection.classList.remove("open");
      feedContainer.style.gridTemplateColumns =
        "repeat(auto-fit, minmax(300px, 1fr))";
      bodyWithoutTitle.style.display = "block";

      anime({
        targets: button,
        scaleX: [0.2, 1.2, 1],
        scaleY: [0.2, 1.2, 1],
        duration: 500,
        easing: "easeInOutQuad",
      });
    } else {
      const postId = button.getAttribute("data-post-id");

      fetch(`/user/${currentUsername}/feed/comment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ post_id: postId }),
      })
        .then((response) => response.json())
        .catch((error) => {
          console.error("Fehler beim Laden:", error);
        });

      anime({
        targets: button,
        scaleX: [0.2, 1.2, 1],
        scaleY: [0.2, 1.2, 1],
        duration: 500,
        easing: "easeInOutQuad",
      });

      const feedContainer = document.getElementById("feed-window");
      const bodyWithoutTitle = document.getElementById("body-without-title");

      commentSection.classList.add("open");
      feedContainer.style.gridTemplateColumns = "1fr";
      bodyWithoutTitle.style.display = "grid";
      bodyWithoutTitle.style.gridTemplateColumns = "1fr 1fr";
    }
  });
});

// 🔥 SCROLL LOGIC (FIXED)
let mostCenteredPost = null;
let oldMostCenteredPost = null;

window.addEventListener("scroll", () => {
  const commentSection = document.getElementById("comment-section");

  if (!commentSection.classList.contains("open")) return;

  const posts = document.getElementsByClassName("img-text-message");
  const windowHeight = window.innerHeight;

  let newMostCenteredPost = posts[0];

  for (let i = 0; i < posts.length; i++) {
    const rect = posts[i].getBoundingClientRect();
    const elementMiddleY = rect.top + rect.height / 2;

    const currentRect = newMostCenteredPost.getBoundingClientRect();
    const currentMiddleY = currentRect.top + currentRect.height / 2;

    if (
      Math.abs(elementMiddleY - windowHeight / 2) <
      Math.abs(currentMiddleY - windowHeight / 2)
    ) {
      newMostCenteredPost = posts[i];
    }
  }

  // 👉 HIER DER WICHTIGE FIX
  oldMostCenteredPost = mostCenteredPost;
  mostCenteredPost = newMostCenteredPost;

  // Scale reset
  for (let i = 0; i < posts.length; i++) {
    posts[i].style.scale = "1";
  }

  mostCenteredPost.style.scale = "1.05";

  // nur wenn sich wirklich was geändert hat
  if (oldMostCenteredPost && oldMostCenteredPost !== mostCenteredPost) {
    const postId = mostCenteredPost.id;

    fetch(`/user/${currentUsername}/feed/comment`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ post_id: postId }),
    })
      .then((response) => response.json())
      .then((response) => {
        const container = document.getElementById("comment-section");
        container.innerHTML = "<h3>Kommentare</h3>";

        const comments = response.data;

        comments.forEach((comment) => {
          const div = document.createElement("div");
          div.classList.add("comment");
          div.textContent = comment.content;
          container.appendChild(div);
        });
      });
  }
});

// SEND COMMENT
const inputComment = document.getElementById("write_comment");
const sendCommentButton = document.getElementById("send_comment");

sendCommentButton.addEventListener("click", () => {
  const commentInput = inputComment.value;
  const postId = mostCenteredPost?.id;

  fetch(`/user/${currentUsername}/feed/write_comment`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content: commentInput, post_id: postId }),
  })
    .then((response) => response.json())
    .catch((error) => {
      console.error("Fehler beim Kommentar:", error);
    });
});

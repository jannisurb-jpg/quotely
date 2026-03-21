document.querySelectorAll(".like-btn").forEach(button => {

    button.addEventListener("click", () => {
        console.log("Button wurde geklickt! Post-ID:", button.getAttribute("data-post-id"));

        // Schritt 3: Post-ID aus dem data-Attribut des Buttons lesen
        const postId = button.getAttribute("data-post-id");

        // Schritt 4: currentUsername (aus HTML definiert) für die URL verwenden
        fetch(`/user/${currentUsername}/feed/like`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ post_id: postId })
        })

        // Schritt 5: Antwort vom Server als JSON lesen
        .then(response => response.json())

        .then(data => {
            if (data.liked) {
                // Schritt 6a: Like war erfolgreich → Zahl und Button aktualisieren
                document.getElementById(`like-count-${postId}`).innerText = data.likes;
                button.innerText = "❤️";

            } else if (data.error) {
                // Schritt 6b: Server hat einen Fehler gemeldet
                alert(data.error);

            } else {
                // Schritt 6c: Post wurde bereits geliked
                document.getElementById(`like-count-${postId}`).innerText = data.likes;
                button.innerText = "🤍";
            }
        })

        // Schritt 7: Netzwerkfehler abfangen
        .catch(error => {
            console.error("Fehler beim Liken:", error);
        });

        anime({
        targets: button,
        scaleX: [0.2, 1.2, 1],        // horizontal verzerren
        scaleY: [0.2, 1.2, 1],        // vertikal verzerren
        duration: 500,
        easing: 'easeInOutQuad'
        });
    });
});

document.querySelectorAll(".follow-btn").forEach(button => {
    console.log("Follow")

    button.addEventListener("click", () => {

        //Follow Logic
        // Schritt 3: Post-ID aus dem data-Attribut des Buttons lesen
        const id_to_follow = button.getAttribute("data-post-id");

        // Schritt 4: currentUsername (aus HTML definiert) für die URL verwenden
        fetch(`/user/${username_to_follow}/follow`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ id_to_follow: id_to_follow })
        })

        // Schritt 5: Antwort vom Server als JSON lesen
        .then(response => response.json())

        .then(data => {
            const followButton = document.getElementsByClassName('follow-button-container')
            const followButton2 = document.getElementsByClassName('follow-btn')

            if (data.followed) {
                // Schritt 6a: Like war erfolgreich → Zahl und Button aktualisieren
                document.getElementById(`follower-count-${id_to_follow}`).innerText = "Follower: " + data.follower;
                button.innerText = "Gefolgt"

                anime({
                targets: followButton,
                scaleX: [0.2, 1.2, 1],        // horizontal verzerren
                scaleY: [0.2, 1.2, 1],        // vertikal verzerren
                backgroundColor: ['#ff0000', '#ffffff'],
                outlineColor: ['#ff0000', '#ffffff'],
                duration: 500,
                easing: 'easeInOutQuad'
            });

            anime({
                targets: followButton2,
                color: ['#ffffff', '#ff0000'],
                duration: 500,
                easing: 'easeInOutQuad'
            });

            } else if (data.error) {
                // Schritt 6b: Server hat einen Fehler gemeldet
                alert(data.error);

            } else {
                // Schritt 6c: Post wurde bereits geliked
                document.getElementById(`follower-count-${id_to_follow}`).innerText = "Follower: " + data.follower;
                button.innerText = "Folgen"

                anime({
                targets: followButton,
                scaleX: [0.2, 1.2, 1],        // horizontal verzerren
                scaleY: [0.2, 1.2, 1],        // vertikal verzerren
                backgroundColor: ['#ffffff', '#ff0000'],
                outlineColor: ['#ffffff', '#ff0000'],
                duration: 500,
                easing: 'easeInOutQuad'
            });

            anime({
                targets: followButton2,
                color: ['#ff0000', '#ffffff'],
                duration: 500,
                easing: 'easeInOutQuad'
            });
            }
        })

        // Schritt 7: Netzwerkfehler abfangen
        .catch(error => {
            console.error("Fehler beim Liken:", error);
        });    
    });
});

const button = document.getElementById("search-user");
const buttonSearch = document.querySelector(".search")
const inputField = document.querySelector(".search-user-input");
const durationSearchBar = 200
button.addEventListener("click", () => {
    if(inputField.classList.contains("open")) {
        console.log("activated animation at:", performance.now());
        anime.set(inputField, {
        transformOrigin: 'left bottom'
        });
        anime({
            targets: [inputField, buttonSearch],
            duration: durationSearchBar,
            translateY: {
                value: [0, "200%"],
                easing: 'linear'
            },
            translateX: '-50%',
            scaleX:{
                value:['100%', '.5%'],
                easing: 'easeOutExpo'
            },
            scaleY:{
                value:['100%', '5%'],
                easing: 'easeOutExpo'
            },
            complete: () => {
                console.log("complete fired at:", performance.now());
                inputField.classList.remove("open");
                buttonSearch.classList.remove("open");
            }
        })
    }
    else {
        inputField.classList.add("open");
        buttonSearch.classList.add("open");
        anime.set(inputField, {
        transformOrigin: 'left bottom'
        });
        anime({
        targets:[inputField, buttonSearch],
        translateY: {
            value: ["200%", 0],
            duration:durationSearchBar,
            easing: 'linear'
        },
        translateX: ['-50%', '-50%'],
        scaleX:{
            value:['.5%', '100%'],
            duration:durationSearchBar,
            easing: 'easeInExpo'
        },
        scaleY:{
            value:['5%', '100%'],
            duration:durationSearchBar,
            easing: 'easeInExpo'
        },
    })
    }
});

document.querySelectorAll(".comments-btn").forEach(button => {

    button.addEventListener("click", () => {
        console.log("Button wurde geklickt! Post-ID:", button.getAttribute("data-post-id"));

        // Schritt 3: Post-ID aus dem data-Attribut des Buttons lesen
        const postId = button.getAttribute("data-post-id");

        // Schritt 4: currentUsername (aus HTML definiert) für die URL verwenden
        fetch(`/user/${currentUsername}/feed/comment`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ post_id: postId })
        })

        // Schritt 5: Antwort vom Server als JSON lesen
        .then(response => response.json())

        // Schritt 7: Netzwerkfehler abfangen
        .catch(error => {
            console.error("Fehler beim Liken:", error);
        });

        anime({
        targets: button,
        scaleX: [0.2, 1.2, 1],        // horizontal verzerren
        scaleY: [0.2, 1.2, 1],        // vertikal verzerren
        duration: 500,
        easing: 'easeInOutQuad'
        });

        const commentSection = document.getElementById('comment-section');
        const feedContainer = document.getElementById('feed-window');
        const bodyWithoutTitle = document.getElementById('body-without-title');

        commentSection.classList.add("open")
        feedContainer.style.gridTemplateColumns = '1fr';
        bodyWithoutTitle.style.display = 'grid';
        bodyWithoutTitle.style.gridTemplateColumns = '1fr 1fr'
    });
});

let mostCenteredPost = null;
window.addEventListener('scroll', () => {
    if(document.getElementById('comment-section').classList.contains("open")) {
        const posts = document.getElementsByClassName('img-text-message');
    windowHeight = window.innerHeight;

    mostCenteredPost = posts[1];
    for(let i = 0; i < posts.length; i++) {
        const rect = posts[i].getBoundingClientRect();
        const elementMiddleY = rect.top + rect.height / 2;

        if(Math.abs(elementMiddleY - windowHeight/2) < Math.abs((mostCenteredPost.getBoundingClientRect().top + mostCenteredPost.getBoundingClientRect().height / 2) - windowHeight/2)) {
            mostCenteredPost = posts[i];
        }
    }

    for(let i = 0; i < posts.length; i++) {

        if(posts[i] != mostCenteredPost) {
            posts[i].style.scale = '1';
        }
    }

    mostCenteredPost.style.scale = '1.05';

    const postId = mostCenteredPost.id;

    fetch(`/user/${currentUsername}/feed/comment`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ post_id: postId })
        })
        .then(response => response.json())

        .then(response => { 
            const container = document.getElementById('comment-section');
            container.innerHTML = '<h3>Kommentare</h3>'; // Container leeren!
            const comments = response.data;

            comments.forEach(comment => {
                const div = document.createElement('div');
                div.classList.add('comment');
                div.textContent = comment.content;
                container.appendChild(div);
            });
        });
    }
});

const inputComment = document.getElementById("write_comment");
const sendCommentButton = document.getElementById("send_comment");

sendCommentButton.addEventListener("click", () => {
        const commentInput = inputComment.value;
        const postId = mostCenteredPost.id;

        // Schritt 4: currentUsername (aus HTML definiert) für die URL verwenden
        fetch(`/user/${currentUsername}/feed/write_comment`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ content: commentInput, post_id: postId})
        })

        // Schritt 5: Antwort vom Server als JSON lesen
        .then(response => response.json())

        // Schritt 7: Netzwerkfehler abfangen
        .catch(error => {
            console.error("Fehler beim Liken:", error);
        });
});
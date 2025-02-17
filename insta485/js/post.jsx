import React, { useState, useEffect } from "react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

// The parameter of this function is an object with a string called url inside it.
// url is a prop for the Post component.
export default function Post({ url }) {
  /* Display image and post owner of a single post */

  dayjs.extend(relativeTime);
  dayjs.extend(utc);

  const [imgUrl, setImgUrl] = useState("");
  const [owner, setOwner] = useState("");
  const [numLikes, setNumLikes] = useState("");
  const [postId, setPostId] = useState("");
  const [lognameLikesThis, setLognameLikesThis] = useState(false);
  const [comments, setComments] = useState([]);
  const [comment, setComment] = useState("");
  const [created, setCreated] = useState("");
  const [postShowUrl, setPostShowUrl] = useState("");
  const [unlikeUrl, setUnlikeURL] = useState("");
  const [ownerImgUrl, setOwnerImgUrl] = useState("");
  const [dataFetched, setDataFetched] = useState(false);

  useEffect(() => {
    // Declare a boolean flag that we can use to cancel the API request.
    let ignoreStaleRequest = false;

    // Call REST API to get the post's information
    fetch(url, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        // If ignoreStaleRequest was set to true, we want to ignore the results of the
        // the request. Otherwise, update the state to trigger a new render.
        if (!ignoreStaleRequest) {
          setImgUrl(data.imgUrl);
          setOwner(data.owner);
          setNumLikes(data.likes.numLikes);
          setPostId(data.postid);
          setLognameLikesThis(data.likes.lognameLikesThis);
          setComments([...comments, ...data.comments]);
          setCreated(dayjs.utc(data.created).local().fromNow());
          setPostShowUrl(data.postShowUrl);
          setUnlikeURL(data.likes.url);
          setOwnerImgUrl(data.ownerImgUrl);
          setDataFetched(true);
        }
      })
      .catch((error) => console.log(error));

    return () => {
      // This is a cleanup function that runs whenever the Post component
      // unmounts or re-renders. If a Post is about to unmount or re-render, we
      // should avoid updating state.
      ignoreStaleRequest = true;
    };
  }, [url]);

  function like(e) {
    e.preventDefault();
    fetch(`/api/v1/likes/?postid=${postId}`, { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        setUnlikeURL(`/api/v1/likes/${data.likeid}/`);
        setNumLikes(numLikes + 1);
        setLognameLikesThis(true);
      });
  }

  function unlike(e) {
    e.preventDefault();
    fetch(unlikeUrl, { method: "DELETE" }).then(() => {
      setNumLikes(numLikes - 1);
      setLognameLikesThis(false);
    });
  }

  function doubleLike(e) {
    e.preventDefault();
    if (!lognameLikesThis) {
      fetch(`/api/v1/likes/?postid=${postId}`, { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        setUnlikeURL(`/api/v1/likes/${data.likeid}/`);
        setNumLikes(numLikes + 1);
        setLognameLikesThis(true);
      })
    }
  }

  function postComment(e) {
    e.preventDefault();
    fetch(`/api/v1/comments/?postid=${postId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: comment,
      }),
    })
      .then((response) => {
        return response.json();
      })
      .then((data) => {
        setComments((comments) => [...comments, data]);
      })
      .catch((error) => {
        console.error("Error posting comment:", error);
      });
  }

  function deleteComment(e, commentid) {
    e.preventDefault();
    fetch(`/api/v1/comments/${commentid}/`, { method: "DELETE" }).then(() => {
      setComments((comments) =>
        comments.filter((comment) => comment.commentid !== commentid),
      );
    });
  }

  // Render post image and post owner
  return (
    <div className="post">
      <div className="owner" style={{ display: 'flex' }}>
        <img src={ownerImgUrl} alt="owner_image" style={{ width: '50px', height: '50px' }} />
        <p>
          {owner} <a href={postShowUrl}>{created}</a>
        </p>
      </div>
      <img
        src={imgUrl}
        alt="post_image"
        onDoubleClick={(e) => {
          doubleLike(e);
        }}
      />
      <p>
        {numLikes} {numLikes == 1 ? "like" : "likes"}
      </p>
      {dataFetched ? 
        <>
          {lognameLikesThis ? (
          <button
            data-testid="like-unlike-button"
            onClick={(e) => {
              unlike(e);
            }}
          >
            Unlike
          </button>
        ) : (
          <button
            data-testid="like-unlike-button"
            onClick={(e) => {
              like(e);
            }}
          >
            Like
          </button>
        )}
        {comments.map((c) => {
          return (
            <div
              data-testid="comment-text"
              style={{ display: "flex", alignItems: "center" }}
              className="comment"
              key={c.commentid}
            >
              <a
                style={{ fontWeight: "bold", marginRight: "10px" }}
                href={c.ownerShowUrl}
              >
                {c.owner}
              </a>
              <p style={{ marginRight: "10px" }}>{c.text}</p>
              {c.lognameOwnsThis ? (
                <button
                  data-testid="delete-comment-button"
                  onClick={(e) => {
                    deleteComment(e, c.commentid);
                  }}
                >
                  Delete
                </button>
              ) : (
                <></>
              )}
            </div>
          );
        })}
        <form
        data-testid="comment-form"
        onSubmit={(e) => {
          postComment(e);
        }}
      >
        <input
          type="text"
          onChange={(e) => {
            setComment(e.target.value);
          }}
        />
      </form>
        </> : <></>
      }
      
    </div>
  );
}

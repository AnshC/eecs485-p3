import React, { useState, useEffect } from "react";
import Post from "./post";
import InfiniteScroll from "react-infinite-scroll-component";

export default function Feed() {
  const [posts, setPosts] = useState([]);
  const [nextURL, setNext] = useState();

  // Initial Fetch
  useEffect(() => {
    fetch("/api/v1/posts/")
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        setPosts([...posts, ...data.results]);
        setNext(data.next);
      });
  }, []);

  // Next Fetch
  function getNextPosts() {
    if (nextURL) {
      fetch(nextURL)
        .then((response) => {
          return response.json();
        })
        .then((data) => {
          setPosts([...posts, ...data.results]);
          setNext(data.next);
        });
    }
  }

  return (
    <div className="feed">
      <div className="nav">
        <h1>Insta485</h1>
      </div>
      <div className="posts">
        <InfiniteScroll
          dataLength={posts.length}
          next={getNextPosts}
          hasMore={!!nextURL}
          loader={<h4>Loading...</h4>}
          endMessage={
            <p style={{ textAlign: "center" }}>
              <b>Yay! You have seen it all</b>
            </p>
          }
        >
          {posts.map((post) => {
            return <Post url={post.url} key={post.postid} />;
          })}
        </InfiniteScroll>
      </div>
    </div>
  );
}

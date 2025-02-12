import React, { useState, useEffect } from "react";
import "../static/css/style.css"
import Post from "./post";
export default function Feed() {

    const [posts, setPosts] = useState([])

    useEffect(()=>{

        fetch("/api/v1/posts/").then((response)=>{
            if (!response.ok) throw Error(response.statusText);
            return response.json();
        }).then((data)=>{
            setPosts([...posts, ...data.results]);
        })

    }, [])

    return (
        <div className="feed">
            <div className="nav">
                <h1>Insta485</h1>
            </div>
            <div className="posts">
                {posts.map((post)=>{
                    return <Post url={post.url} key={post.postid}/>
                })}
            </div>
        </div>
    )
}
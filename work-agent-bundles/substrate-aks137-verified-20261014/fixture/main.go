package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
)

type state struct {
	Memory  int    `json:"memory"`
	Durable int    `json:"durable"`
	Marker  string `json:"marker"`
}

func main() {
	if err := os.MkdirAll("/data", 0755); err != nil {
		log.Fatal(err)
	}
	var current state
	if data, err := os.ReadFile("/data/state.json"); err == nil {
		if err := json.Unmarshal(data, &current); err != nil {
			log.Fatal(err)
		}
		current.Memory = 0
	} else if !os.IsNotExist(err) {
		log.Fatal(err)
	}
	var mu sync.Mutex
	http.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) { fmt.Fprintln(w, "ready") })
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		if r.Method != http.MethodPost {
			http.Error(w, "POST required", 405)
			return
		}
		if current.Marker == "" {
			current.Marker = r.Header.Get("X-Proof-Marker")
		}
		if current.Marker == "" {
			http.Error(w, "synthetic marker required", 400)
			return
		}
		current.Memory++
		current.Durable++
		data, err := json.Marshal(current)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		file, err := os.OpenFile("/data/state.json", os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		_, err = file.Write(data)
		if err == nil {
			err = file.Sync()
		}
		closeErr := file.Close()
		if err == nil {
			err = closeErr
		}
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if _, err := w.Write(data); err != nil {
			log.Print(err)
		}
	})
	log.Fatal(http.ListenAndServe(":80", nil))
}

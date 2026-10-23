#!/usr/bin/env ruby
# frozen_string_literal: true

# Optional companion JSON filter for YTSDownloader.
# Reads stdin (JSON object/array, NDJSON, or free text), writes cleaned NDJSON items.
# Used when Ruby is on PATH; Python falls back to its own parser if this fails.

require "json"
require "uri"

URL_RE = %r{https?://[^\s<>"']+}i

def clean_url(raw)
  s = raw.to_s.strip.sub(/[).,;\]'"]+\z/, "")
  uri = URI.parse(s)
  return nil unless %w[http https].include?(uri.scheme) && uri.host
  s
rescue URI::InvalidURIError
  nil
end

def item_from_hash(h)
  url = clean_url(h["url"] || h["href"] || h["media_url"] || "")
  return nil unless url
  {
    "url" => url,
    "title" => (h["title"] || h["name"] || "").to_s.strip,
    "source" => (h["source"] || h["origin"] || "").to_s.strip,
    "page_url" => (h["page_url"] || h["referrer"] || "").to_s.strip
  }
end

def items_from_list(arr)
  arr.filter_map do |v|
    case v
    when String
      u = clean_url(v)
      u ? { "url" => u, "title" => "", "source" => "", "page_url" => "" } : nil
    when Hash
      item_from_hash(v)
    end
  end
end

def parse_payload(text)
  text = text.to_s.strip
  return [] if text.empty?

  if text.start_with?("{", "[")
    begin
      data = JSON.parse(text)
      case data
      when Hash
        if data.key?("url") || data.key?("href") || data.key?("media_url")
          it = item_from_hash(data)
          return it ? [it] : []
        end
        %w[urls items links].each do |key|
          return items_from_list(data[key]) if data[key].is_a?(Array)
        end
      when Array
        return items_from_list(data)
      end
    rescue JSON::ParserError
      # fall through to line / URL scan
    end
  end

  out = []
  saw_json = false
  text.each_line do |raw|
    line = raw.strip
    next if line.empty? || line.start_with?("#")

    if line.start_with?("{", "[")
      begin
        data = JSON.parse(line)
        saw_json = true
        case data
        when Hash
          it = item_from_hash(data)
          out << it if it
        when Array
          out.concat(items_from_list(data))
        when String
          u = clean_url(data)
          out << { "url" => u, "title" => "", "source" => "", "page_url" => "" } if u
        end
        next
      rescue JSON::ParserError
        # treat as free text
      end
    end
    line.scan(URL_RE).each do |m|
      u = clean_url(m)
      out << { "url" => u, "title" => "", "source" => "", "page_url" => "" } if u
    end
  end

  unless saw_json || !out.empty?
    text.scan(URL_RE).each do |m|
      u = clean_url(m)
      out << { "url" => u, "title" => "", "source" => "", "page_url" => "" } if u
    end
  end
  out
end

def dedupe(items)
  seen = {}
  items.each_with_object([]) do |it, acc|
    u = it["url"]
    next if u.nil? || u.empty? || seen[u]
    seen[u] = true
    acc << it
  end
end

items = dedupe(parse_payload($stdin.read))
items.each { |it| puts JSON.generate(it) }
